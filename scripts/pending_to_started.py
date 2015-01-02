import logging, os, sys
import cherrypy as cp
import daemon
import statsfair.util as sfutil
import statsfair.pers.sfapp as sfapp
from pprint import pprint

LOGGER = logging.getLogger(__name__)
ROOT_DIR = os.path.dirname(__file__)

def pending_to_started():
	LOGGER.info('Start: pending_to_started')
	with sfutil.get_session('sfapp') as sfapp_sess:
		print (	sfapp_sess.query(sfapp.Bet)
					.join(sfapp.Bet.user)
					.join(sfapp.Bet.starting_odds_inst)
					.filter(sfapp.Bet.status == sfapp.Bet.PENDING)
					.filter(sfapp.User.id == 5)
		).first()
		
	LOGGER.info('End: pending_to_started')

if __name__ == '__main__':

	daemon = daemon.Daemon(
			logpath = os.path.join(ROOT_DIR, sys.argv[0] + '.log'),
			update_interval_seconds = 1,
			f = pending_to_started,
			level = logging.DEBUG,
			also_log_to_stderr = 1)

	daemon.start()


