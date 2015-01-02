import logging, os, urllib, random, numpy, collections, datetime
import itertools, time, profile, json, contextlib, decimal
import cherrypy as cp
import mako.template as mt
import mako.lookup as ml
import sqlalchemy as sqla
import sqlalchemy.orm as sqlo
from passlib.apps import custom_app_context as pwd_context
import webutil
import sfapp

LOGGER = logging.getLogger(__name__)

ROOT_DIR = os.path.dirname(__file__)
ENCODING = 'utf-8'

INITIAL_BALANCE = 1000.

lookup = ml.TemplateLookup(directories = [
	os.path.join(ROOT_DIR, 'tmpl'),
])

engines = { }
session_classes = { }

def html(f):
	def f_(self, *args, **kwargs):
		cp.response.headers['content-type'] = 'text/html;charset=' + ENCODING
		return f(self, *args, **kwargs)
	return f_

def db(config_name):
	def to_return(f):
		def f_(self, *args, **kwargs):
			t0 = time.time()
			with webutil.get_conn(config_name) as conn:
				LOGGER.info('Time taken for connecting to db: %.3f', time.time() - t0)
				setattr(cp.thread_data, 'db:' + config_name, conn)
				try:
					return f(self, *args, **kwargs)
				except cp.HTTPRedirect as r:
					conn.commit()
					raise
		return f_
	return to_return

@contextlib.contextmanager
def session_scope(Session):
	session = Session()
	try:
		yield session
		session.commit()
	except:
		session.rollback()
		raise
	finally:
		session.close()

def session(config_name):
	def to_return(f):
		def f_(self, *args, **kwargs):
			engine, Session = get_engine_and_session_class(config_name)
			with session_scope(Session) as session:
				setattr(cp.thread_data, config_name, session)
				cp.thread_data.user = get_user()
				try:
					return f(self, *args, **kwargs)
				except cp.HTTPRedirect as r:
					session.commit()
					raise
		return f_
	return to_return


def get_engine_and_session_class(config_section):
	if config_section in engines:
		return engines[config_section], session_classes[config_section]
	conn_string = cp.request.app.config.get(config_section).get('conn.string')
	engine = sqla.create_engine(conn_string, echo = True)
	engines[config_section] = engine
	session_class = sqlo.sessionmaker(bind = engine)
	session_classes[config_section] = session_class
	return engine, session_class

class StatsfairException(Exception):
	pass

class RegistrationException(StatsfairException):
	pass

class LoginException(StatsfairException):
	pass

class BetException(StatsfairException):
	pass

def json_response(f):
	def to_return(*args, **kwargs):
		cp.response.headers['content-type'] = 'application/json'
		try:
			res = f(*args, **kwargs)
			return json.dumps(
					res,
					sort_keys = True,
					indent = 1,
			)
		except Exception as exc:
			raise #TODO
			return json.dumps({
				'exc': {'type': str(type(exc)), 'msg' : str(exc)}
			})
	return to_return


def create_user(username, password):
	username = username.strip()
	if len(username) <= 2:
		raise RegistrationException('Username is too short.')
	if len(password) <= 3:
		raise RegistrationException('Password is too short.')
	pwhash = pwd_context.encrypt(password)
	user = sfapp.User(username = username, pwhash = pwhash)
	cp.thread_data.sfapp.add(user)

	initbalance = sfapp.InitBalance(user = user, balance = INITIAL_BALANCE)
	cp.thread_data.sfapp.add(initbalance)


def login(username, password):
	username = username.strip()
	user = cp.thread_data.sfapp.query(sfapp.User).filter_by(username = username).one()
	if not pwd_context.verify(password, user.pwhash):
		raise LoginException('Wrong password provided')
	cp.session['userid'] = user.id

def logout():
	cp.session.pop('userid', 0)

def printfoo(*args):
	import pprint
	print 'FOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO'
	print pprint.pprint(*args)
	print 'FOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO'
	print

def get_user():
	userid = cp.session.get('userid')
	if userid:
		return cp.thread_data.sfapp.query(sfapp.User).filter_by(id = userid).one()


def get_balance():
	user = cp.thread_data.user
	userid = user.id
	initbalance = cp.thread_data.sfapp.query(sfapp.InitBalance).filter_by(userid = userid).one().balance
	transactions_sum = sum(tr.amount for tr in user.transactions)
	balance = initbalance + transactions_sum
	printfoo(balance)
	return balance


def create_bet(oddsid, stake, duration):
	balance = get_balance()

	if balance < stake:
		raise BetException('Insufficient balance for this bet.')

	odds_instance = cp.thread_data.sfapp.query(sfapp.Odds).filter_by(id = oddsid).one()

# Let's not do this... Let's do an automatic update just before someone submits
	# a bet, and then this check will be made by the script that changes status
	# to the bets.
	# later_odds = (	cp.thread_data.sfapp.query(sfapp.Odds)
	# 					.filter(sfapp.Odds.eventid == odds_instance.eventid)
	# 					.filter(sfapp.Odds.periodnumber == odds_instance.periodnumber)
	# 					.filter(sfapp.Odds.contestantnum == odds_instance.contestantnum)
	# 					.filter(sfapp.Odds.type == odds_instance.type)
	# 					.filter(sfapp.Odds.vhdou == odds_instance.vhdou)
	# 					.filter(sfapp.Odds.snapshotdate > odds_instance.snapshotdate)
	# ).order_by(sfapp.Odds.snapshotdate.desc()).first()

	print odds_instance

	bet = sfapp.Bet(userid = cp.thread_data.user.id, starting_oddsid = oddsid,
						stake = stake, duration = duration, status = 'P',
						placedat = datetime.datetime.utcnow())

	transaction = sfapp.Transaction(userid = cp.thread_data.user.id,
									amount = -stake,
									date = datetime.datetime.utcnow())

	cp.thread_data.sfapp.add(bet)
	cp.thread_data.sfapp.add(transaction)


class Application:

	@cp.expose
	@html
	@session('pinndb')
	@webutil.template('layout.html', lookup)
	def index(self, *args, **kwargs):
		return {
				'res': None,
		}

	@cp.expose
	@json_response
	@session('sfapp')
	def create_user(self, *args, **kwargs):
		return create_user(kwargs.get('username'), kwargs.get('password'))

	@cp.expose
	@json_response
	@session('sfapp')
	def login(self, *args, **kwargs):
		return login(kwargs.get('username'), kwargs.get('password'))

	@cp.expose
	@json_response
	def logout(self, *args, **kwargs):
		return logout()

	@cp.expose
	@json_response
	@session('sfapp')
	def create_bet(self, *args, **kwargs):
		return create_bet(
				kwargs.get('oddsid'), decimal.Decimal(kwargs.get('stake')), kwargs.get('duration')
		)

if __name__ == '__main__':
	logging.basicConfig(level = logging.DEBUG)
	config_path = os.path.join(ROOT_DIR, 'config')
	application = Application()
	#application = ApplicationBeBackSoon()
	cp.quickstart(
			application,
			'',
			config = config_path
	)

