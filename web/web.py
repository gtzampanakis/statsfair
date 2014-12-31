import logging, os, urllib, random, numpy, collections, itertools, time, profile, json
import cherrypy as cp
import mako.template as mt
import mako.lookup as ml
from passlib.apps import custom_app_context as pwd_context
import webutil

LOGGER = logging.getLogger(__name__)

ROOT_DIR = os.path.dirname(__file__)
ENCODING = 'utf-8'

lookup = ml.TemplateLookup(directories = [
	os.path.join(ROOT_DIR, 'tmpl'),
])

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
			return json.dumps({
				'exc': {'type': str(type(exc)), 'msg' : str(exc)}
			})
	return to_return


def create_user(username, password):
	sql = ''' select 1 from users where lower(username) = lower(%s) '''
	if cp.thread_data.sfapp.execute(sql, [username]).fetchone():
		raise RegistrationException('Username is already used')
	sql = '''
		insert into users
		(username, pwhash)
		values
		(%s, %s)
	'''
	pwhash = pwd_context.encrypt(password)
	pars = [username, pwhash]
	cp.thread_data.sfapp.execute(sql, pars)

def login(username, password):
	sql = '''select id, pwhash from users where lower(username) = lower(%s)'''
	pars = [username]
	row = cp.thread_data.sfapp.execute(sql, pars).fetchone()
	if row:
		userid, pwhash = row
	if not pwd_context.verify(password, pwhash):
		raise LoginException('Wrong password provided')
	cp.session['userid'] = userid

def logout():
	cp.session.pop('userid', 0)


class Application:

	@cp.expose
	@html
	@db('pinndb')
	@webutil.template('layout.html', lookup)
	def index(self, *args, **kwargs):
		res = cp.thread_data.pinndb.execute('select * from gamesdenorm limit 5').fetchall()
		return {
				'res': (res),
		}

	@cp.expose
	@json_response
	@db('sfapp')
	def create_user(self, *args, **kwargs):
		return create_user(kwargs.get('username'), kwargs.get('password'))

	@cp.expose
	@json_response
	@db('sfapp')
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

