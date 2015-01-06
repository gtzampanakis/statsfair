import os, contextlib, logging

LOGGER = logging.getLogger()

PENDING_LIFESPAN = 80
SAFETY_WAIT_PERIOD = 80

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

def get_candidate_odds(oddsid):
	import cherrypy as cp
	import statsfair.pers.sfapp as sfapp

	odds_instance = cp.thread_data.sfapp.query(sfapp.Odds).filter_by(id = oddsid).one()
	LOGGER.debug('odds_instance: %s', odds_instance)

	candidate_odds = (
		cp.thread_data.sfapp
		.query(sfapp.Odds)
		.join(sfapp.Snapshot)
		.join(sfapp.Event)
		.filter(sfapp.Odds.eventid == odds_instance.eventid)
		.filter(sfapp.Odds.periodnumber == odds_instance.periodnumber)
		.filter(sfapp.Odds.contestantnum == odds_instance.contestantnum)
		.filter(sfapp.Odds.type == odds_instance.type)
		.filter(sfapp.Odds.vhdou == odds_instance.vhdou)
		.filter(sfapp.Odds.snapshotdate > odds_instance.snapshotdate)
		.filter(sfapp.Odds.snapshotdate <= sfapp.Event.date)
		.filter(sfapp.Snapshot.mlmax > 0)
		.order_by(sfapp.Odds.snapshotdate)
	)

	return candidate_odds
