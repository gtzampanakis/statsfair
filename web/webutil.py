import datetime, collections, logging, os, re, dbapiutil

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


if __name__ == '__main__':
	pass
