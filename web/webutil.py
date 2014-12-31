import datetime, collections, logging, os, re

LOGGER = logging.getLogger(__name__)

def date_str_to_date(date_str):
	if date_str is None: return None
	return datetime.date(year = int(date_str[:4]),
		month = int(date_str[5:7]),
		day = int(date_str[-2:])
	)

def get_callers_path():
	"""Returns the path of the file of the module that called 
	this function's calling function"""
	import inspect
	result = os.path.dirname(inspect.getouterframes(inspect.currentframe())[2][1])
	return result

def datetime_to_date_str(dt):
	return datetime.datetime.strftime(
		dt, '%Y-%m-%d %H:%M'
	)


def execute_template(tmpl, dict_, encoding = 'utf-8'):
	try:
		return tmpl.render(output_encoding = encoding, **dict_)
	except:
		import sys
		import cherrypy as cp
		from mako import exceptions
		cp.response.status = 500
		s = exceptions.text_error_template().render(output_encoding = encoding)
		sys.stderr.write(s)
		return exceptions.html_error_template().render(output_encoding = encoding)

def template(path, lookup = None, encoding = 'utf-8'):
	import cherrypy
	import mako.lookup as ml
	if lookup is None:
		lookup = ml.TemplateLookup(directories = [
			get_callers_path()
		])
	def execute_template_(f):
		def t(*args, **kwargs):
			try:
				pars = f(*args, **kwargs)
				return lookup.get_template(path).render(output_encoding = encoding, **pars)
			except cherrypy.HTTPRedirect as r:
				raise
			except Exception as e:
				import sys
				from mako import exceptions
				cherrypy.response.status = 500
				s = exceptions.text_error_template().render(output_encoding = encoding)
				sys.stderr.write(s)
				LOGGER.exception(e)
				if cherrypy.request.config.get('show.stacktraces'):
					return exceptions.html_error_template().render(output_encoding = encoding)
				else:
					h = '''
					<!DOCTYPE html>
					<html>
					<head><title>Error</title></head>
					<body>An internal server error occured.</body>
					</html>
					'''
					return h
					
		return t
	return execute_template_

def obj_to_json_string(obj, indent = None):
	import json
	return json.dumps(
			obj,
			sort_keys = True,
			indent = indent,
	)

def rest(f):
	def f_(self, *args, **kwargs):
		import cherrypy
		cherrypy.response.headers['content-type'] = 'application/json'
		return obj_to_json_string(f(self, *args, **kwargs))
	return f_

def get_conn(config_section):
	import cherrypy as cp
	elements = cp.request.app.config[config_section]
	pars_to_pass = { }
	for key, val in elements.iteritems():
		if key.startswith('conn.'):
			pars_to_pass[key[5:]] = val
	import importlib
	db_module = importlib.import_module(elements['driver'])
	conn = db_module.connect(**pars_to_pass)
	return conn

if __name__ == '__main__':
	pass
