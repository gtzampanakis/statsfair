import os, contextlib

PENDING_LIFESPAN = 300
SAFETY_WAIT_PERIOD = 300

def get_web_config():
	import cherrypy.lib.reprconf
	file_path = os.environ.get('STATSFAIR_CONFIG_FILE')
	return cherrypy.lib.reprconf.Config(file_path)

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

engines = { }
session_classes = { }

def get_session(config_section):
	import sqlalchemy as sqla
	import sqlalchemy.orm as sqlo
	config = get_web_config()
	conn_string = config.get(config_section).get('conn.string')
	engine = engines.get(config_section) or sqla.create_engine(conn_string, echo = True)
	session_class = session_classes.get(config_section) or sqlo.sessionmaker(bind = engine)
	engines[config_section] = engine
	session_classes[config_section] = session_class
	return session_scope(session_class)
