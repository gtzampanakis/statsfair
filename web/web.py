import logging, os, urllib, random, numpy, collections, itertools, time, profile
import cherrypy as cp
import mako.template as mt
import mako.lookup as ml
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

def db(f):
	def f_(self, *args, **kwargs):
		t0 = time.time()
		with webutil.get_conn('pinndb') as conn:
			LOGGER.info('Time taken for connecting to db: %.3f', time.time() - t0)
			cp.thread_data.conn = conn
			try:
				return f(self, *args, **kwargs)
			except cp.HTTPRedirect as r:
				conn.commit()
				raise
	return f_


class Application:

	@cp.expose
	@html
	@db
	@webutil.template('layout.html', lookup)
	def index(self, *args, **kwargs):
		return { }

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

