import logging, os, urllib, random, numpy, collections, datetime, collections
import itertools, time, profile, json, contextlib, decimal
import cherrypy as cp
import mako.template as mt
import mako.lookup as ml
import sqlalchemy as sqla
import sqlalchemy.orm as sqlo
from passlib.apps import custom_app_context as pwd_context
import webutil
import statsfair.pers.sfapp as sfapp

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
def session_scope(session_class):
	session = session_class()
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
				setattr(cp.thread_data, 'engine_' + config_name, engine)
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

	odds_instance = (cp.thread_data.sfapp.
						query(sfapp.Odds).join(sfapp.Snapshot)
						.filter(sfapp.Odds.id == oddsid)
	).one()

	bet = sfapp.Bet(userid = cp.thread_data.user.id, starting_oddsid = oddsid,
						stake = stake, duration = duration, status = sfapp.Bet.PENDING,
						placedat = datetime.datetime.utcnow())

	transaction = sfapp.Transaction(userid = cp.thread_data.user.id,
									amount = -stake,
									date = datetime.datetime.utcnow(),
									description = sfapp.Transaction.BET_SUBMIT_STAKE,
	)

	cp.thread_data.sfapp.add(bet)
	cp.thread_data.sfapp.add(transaction)

AVAILABLE_BETS_COLUMN = [
		'evdate', 'sporttype', 'league',
		'hprice', 'pahname', 'dprice',
		'pavname', 'vprice', 'betlimit',
		'hid', 'did', 'vid'
]
AvailableBet = collections.namedtuple('AvailableBet', AVAILABLE_BETS_COLUMN)

def get_available(extra_filter = None):
	conn = cp.thread_data.engine_sfapp.connect()
	sql = '''
	select
	evdate,
	sporttype,
	league,
	round(hprice, 3) hprice,
	pahname,
	round(dprice, 3) dprice,
	pavname,
	round(vprice, 3) vprice,
	betlimit,
	hid,
	did,
	vid
	from pinn.gamesdenorm where 
	penumber = 0
	and bettype = 'm' 
	and evdate > utc_timestamp
	and latest = 1
	and sporttype <> 'E Sports'
	and pahname not like '%%.5 Set%%'
	and ({extra_filter})
	order by
	evdate, sporttype, league,
	pahname, pavname, evid
	limit 20000
	'''.format(extra_filter = extra_filter or '1=1')
	raw = conn.execute(sql).fetchall()

	available = [ ]
	
	for raw_row in raw:
		available_row = AvailableBet(*raw_row)
		available.append(available_row)

	return available
		

class Application:

	@cp.expose
	@html
	@session('sfapp')
	@webutil.template('index.html', lookup)
	def index(self, *args, **kwargs):
		available = get_available()
		return {
				'available' : available,
		}

	@cp.expose
	@html
	@session('sfapp')
	@webutil.template('stakes.html', lookup)
	def stakes(self, *args, **kwargs):
		oddsid = kwargs.get('oddsid')
		extra_filter = str(oddsid) + ' in (hid, did, vid)'
		available = get_available(extra_filter)
		to_return = {
				'available' : available,
		}
		if len(available) == 0:
			pass # TODO
		else:
			row = available[0]
			for id_name, price_name in zip(['hid', 'did', 'vid'], ['hprice', 'dprice', 'vprice']):
				if oddsid == str(getattr(row, id_name)):
					to_return['selected'] = price_name
		return to_return


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
	cp.quickstart(
			application,
			'',
			config = config_path
	)

