import logging, os, urllib, random, numpy, collections, itertools, time, profile, json, contextlib
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
				setattr(cp.thread_data, config_name, conn)
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

class RegistrationException(Exception):
	pass

class LoginException(Exception):
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
	pwhash = pwd_context.encrypt(password)
	user = sfapp.User(username = username, pwhash = pwhash)
	cp.thread_data.sfapp.add(user)


def login(username, password):
	# sql = '''select id, pwhash from users where lower(username) = lower(%s)'''
	# pars = [username]
	# row = cp.thread_data.sfapp.execute(sql, pars).fetchone()
	user = cp.thread_data.sfapp.query(sfapp.User).filter_by(username = username).one()
	if not pwd_context.verify(password, user.pwhash):
		raise LoginException('Wrong password provided')
	cp.session['userid'] = user.id

def logout():
	cp.session.pop('userid', 0)


class Application:

	@cp.expose
	@html
	@session('pinndb')
	@webutil.template('layout.html', lookup)
	def index(self, *args, **kwargs):
		res = cp.thread_data.pinndb.execute('select * from gamesdenorm limit 5').fetchall()
		return {
				'res': (res),
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

