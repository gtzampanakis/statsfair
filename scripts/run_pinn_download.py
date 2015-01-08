import logging, os, sys
import daemon
import statsfair.pinndown.pinnacle_download as pd

LOGGER = logging.getLogger(__name__)
ROOT_DIR = os.path.dirname(__file__)

if __name__ == '__main__':

	def call_when_update_done(systemdate):
		from statsfair.scripts.pending_to_started import pending_to_started
		LOGGER.info('Calling pending_to_started with systemdate: %s', systemdate)
		pending_to_started(systemdate)
	def f():
		pd.Downloader(60., call_when_update_done).start()

	daemon = daemon.Daemon(
			logpath = os.path.join(ROOT_DIR, sys.argv[0] + '.log'),
			update_interval_seconds = 5 * 60.,
			f = f,
			level = logging.DEBUG,
			also_log_to_stderr = 1)

	daemon.start()


