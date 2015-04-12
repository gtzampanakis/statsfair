import time, os, logging, sqlite3, datetime, logging.handlers, collections, urllib2, argparse
import xml.etree.ElementTree as etree
import MySQLdb as db_module
import daemon
import commonlib as cl

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_URL = 'http://xml.pinnaclesports.com/pinnacleFeed.aspx?'

ALSO_TO_STDERR = 0

VHDOU_VAL = {
		'Draw' : 'd',
		'Home' : 'h',
		'Visiting' : 'v',
		'draw' : 'd',
		'home' : 'h',
		'visiting' : 'v',
		'over' : 'o',
		'under' : 'u',
		None : None
}

BEFORE_SQL = '''
	update odds
	set opening = null, latest = null
	where odds.periodnumber = %s
	and odds.type = %s
	and odds.eventid = %s;
'''
AFTER_SQL1 = '''
	select odds.id
	from odds
	where odds.periodnumber = %s
	and odds.type = %s
	and odds.eventid = %s
	and exists (
		select 1
		from snapshots snex
		where snex.eventid = odds.eventid
		and snex.periodnumber = odds.periodnumber
		and snex.date = odds.snapshotdate
		and (
			case odds.type
				when 'm' then snex.mlmax
				when 's' then snex.spreadmax
				when 't' then snex.totalmax
			end
		) > 0
	)
	and not exists(
		select 1
		from odds q
		join snapshots sn
				on sn.eventid = q.eventid
				and sn.periodnumber = q.periodnumber
				and sn.date = q.snapshotdate
				and (
					case q.type
						when 'm' then sn.mlmax
						when 's' then sn.spreadmax
						when 't' then sn.totalmax
					end
				) > 0
		where q.periodnumber = odds.periodnumber
		and q.type = odds.type
		and q.eventid = odds.eventid
		and q.snapshotdate < odds.snapshotdate
	)
'''
AFTER_SQL2 = '''
	select odds.id
	from odds
	where odds.periodnumber = %s
	and odds.type = %s
	and odds.eventid = %s
	and exists (
		select 1
		from snapshots snex
		where snex.eventid = odds.eventid
		and snex.periodnumber = odds.periodnumber
		and snex.date = odds.snapshotdate
		and (
			case odds.type
				when 'm' then snex.mlmax
				when 's' then snex.spreadmax
				when 't' then snex.totalmax
			end
		) > 0
	)
	and not exists(
		select 1
		from odds q
		join snapshots sn
				on sn.eventid = q.eventid
				and sn.periodnumber = q.periodnumber
				and sn.date = q.snapshotdate
				and (
					case q.type
						when 'm' then sn.mlmax
						when 's' then sn.spreadmax
						when 't' then sn.totalmax
					end
				) > 0
		where q.periodnumber = odds.periodnumber
		and q.type = odds.type
		and q.eventid = odds.eventid
		and q.snapshotdate > odds.snapshotdate
	)
'''

LOGGER = logging.getLogger(__name__)
ROOT_LOGGER = logging.getLogger()

def capitalize_first(s):
	return s[0].upper() + s[1:]

def period_el_to_contestantnum_rotnum(period_el, event_el, vhdou):
	r = {
			'home' : 'Home',
			'draw' : 'Draw',
			'visiting' : 'Visiting',
			'over' : 'Home',
			'under' : 'Visiting'
	}[vhdou]
	for participants_el in event_el.findall('participants'):
		for participant_el_cand in participants_el.findall('participant'):
			for visiting_home_draw_el in participant_el_cand.findall('visiting_home_draw'):
				if visiting_home_draw_el.text == r:
					participant_el = participant_el_cand
	to_return =  [
			coalesce(participant_el, 'contestantnum', 1),
			coalesce(participant_el, 'rotnum', 1),
	]
	return to_return



def coalesce(etree, xpath, get_text = False):
	elem = etree.findall(xpath)
	if len(elem) != 0:
		assert len(elem) == 1
		res = elem[0]
		if get_text:
			res = res.text
		return res
	return None

def fix_to_base(val):
# There are times where Pinnacle sends a value of -1.79769313486232E+308.  This
# is out of range for MySQL and thus an error is given. This value is obviously
# wrong so setting a value of 0 for them.
	if val == '-1.79769313486232E+308':
		val = 0.
	return val


def dec_odds(amer_odds):
	if amer_odds is None:
		return None
	amer_odds = float(amer_odds)
	if amer_odds == 0:
		return -1
	elif amer_odds > 0:
		return (100 + amer_odds) / 100.
	else:
		return 100 / (-amer_odds) + 1

def get_conn_mysql():

	if os.path.exists(os.path.join(ROOT_DIR, 'pythonanywhere')):
		db_api_conn = db_module.connect(
			host = 'mysql.server',
			user = 'giorgostzampanak',
			passwd = 'foopassword',
			db = 'giorgostzampanak$pinnacle12',
# Even when the default encoding of the database is utf8, we have to use the
# following two options because MySQLdb does not detect encoding and will still
# try to use latin1.
			use_unicode = True,
# Use utf8, without the dash, otherwise MySQLdb gives a "cannot initialize
# charset" error.
			charset = 'utf8',
		)
	else:
		db_api_conn = db_module.connect(
			host = 'localhost',
			user = 'root',
			passwd = 'root',
			db = 'pinn',
# Even when the default encoding of the database is utf8, we have to use the
# following two options because MySQLdb does not detect encoding and will still
# try to use latin1.
			use_unicode = True,
# Use utf8, without the dash, otherwise MySQLdb gives a "cannot initialize
# charset" error.
			charset = 'utf8',
		)


	class Conn:
		pass

	conn = Conn()

	def __enter__():
		return conn

	def __exit__(exc_type, exc_value, traceback):
		if exc_type is not None:
			try:
				conn.db_api_conn.rollback()
			except:
				pass
			conn.db_api_conn.close()

		else:
			try:
				conn.db_api_conn.commit()
			except:
				conn.db_api_conn.close()
				raise
			conn.db_api_conn.close()

		return False

	def execute(sql, params = [ ]):
		cursor = conn.db_api_conn.cursor()
		cursor.execute(sql, params)
		return cursor

	def commit():
		return conn.db_api_conn.commit()

	def explain(sql, params = [ ]):
		return conn.execute('explain ' + sql, params)

	conn.db_api_conn = db_api_conn
	conn.__enter__ = __enter__
	conn.__exit__ = __exit__
	conn.execute = execute
	conn.explain = explain
	conn.commit = commit

	return conn


class Downloader:

	def __init__(self, update_interval, call_when_update_done = None):
		self.update_interval = update_interval
		self.call_when_update_done = call_when_update_done


	def parse_document(self, etree, systemdate):
		query_queue = collections.defaultdict(list)

		systemdate_sqlite_str = systemdate.strftime('%Y-%m-%d %H:%M:%S.%f')


		snapshot_utc_date = datetime.datetime.utcfromtimestamp(
				int(etree.find('PinnacleFeedTime').text) / 1e3
		)
		snapshot_sqlite_str = snapshot_utc_date.strftime('%Y-%m-%d %H:%M:%S.%f')
		for event_el in etree.findall('events/event'):
			islive = coalesce(event_el, 'IsLive', 1)
			eventid = event_el.find('gamenumber').text
			is_contest = len(event_el.findall('contest_maximum')) != 0
			evdate_str = event_el.find('event_datetimeGMT').text
			evdate_dt = datetime.datetime.strptime(evdate_str, '%Y-%m-%d %H:%M')
# For unknown reasons, pinnacle's xml lists some matches as starting on weird
# times like 19:59 and 21:44. This will fix this.
			if evdate_dt.minute % 5 == 4:
				LOGGER.debug('Adding 1 minute to datetime: %s', evdate_dt)
				evdate_dt += datetime.timedelta(minutes = 1)

			def add_args(*args, **kwargs):
				if args[0] == 'odds':
					query_queue[eventid].append([
								BEFORE_SQL,
								[ kwargs['periodnumber'],
								kwargs['type'],
								kwargs['eventid']]
					])
				args_to_append = cl.get_insert_args_mysql(*args, **kwargs)
				query_queue[eventid].append(args_to_append)
				if args[0] == 'odds':
					query_queue[eventid].append([
								AFTER_SQL1,
								[ kwargs['periodnumber'],
								kwargs['type'],
								kwargs['eventid']]
					])
					query_queue[eventid].append([
								AFTER_SQL2,
								[ kwargs['periodnumber'],
								kwargs['type'],
								kwargs['eventid']]
					])

			add_args(
				'events',
				'replace',
				id = eventid,
				date = cl.datetime_to_sqlite_str(evdate_dt),
				sporttype = event_el.find('sporttype').text,
				league = event_el.find('league').text,
				islive = (1 if islive == 'Yes' else 0),
				description = coalesce(event_el, 'description', 1),
			)
			for participant_el in event_el.findall('participants/participant'):
				contestantnum = participant_el.find('contestantnum').text
				rotnum = participant_el.find('rotnum').text
				vhd = coalesce(participant_el, 'visiting_home_draw', 1)
				pitcher = coalesce(participant_el, 'pitcher', 1)
				add_args(
					'participants',
					'replace',
					eventid = eventid,
					contestantnum = contestantnum,
					rotnum = rotnum,
					vhdou = VHDOU_VAL[vhd],
					pitcher = pitcher,	
					name = participant_el.find('participant_name').text,
				)
				if is_contest:
					add_args(
						'snapshots',
						'replace',
						eventid = eventid,
						date = snapshot_sqlite_str,
						systemdate = systemdate_sqlite_str,
						mlmax = int(coalesce(event_el, 'contest_maximum', 1)),
					)
					add_args(
						'odds',
						'replace',
						eventid = eventid,
						periodnumber = None,
						snapshotdate = snapshot_sqlite_str,
						type = 'm',
						threshold = 0,
						vhdou = None,
						price = dec_odds(
							coalesce(
								participant_el, 'odds/moneyline_value', 1
							)
						),
						to_base = fix_to_base(coalesce(
									participant_el, 'odds/to_base', 1
						)),
						contestantnum = contestantnum,
						rotnum = rotnum,

					)
				
			if not is_contest:
				for period_el in event_el.findall('periods/period'):
					periodnumber = period_el.find('period_number').text
					add_args(
						'periods',
						'replace',
						eventid = eventid,
						number = periodnumber,
						description = period_el.find('period_description').text,
						cutoff = period_el.find('periodcutoff_datetimeGMT').text,
					)
					add_args(
						'snapshots',
						'replace', 
						eventid = eventid,
						periodnumber = periodnumber,
						date = snapshot_sqlite_str,
						systemdate = systemdate_sqlite_str,
						status = period_el.find('period_status').text,
						upd = period_el.find('period_update').text,
						spreadmax = int(float(period_el.find('spread_maximum').text)),
						mlmax = int(float(period_el.find('moneyline_maximum').text)),
						totalmax = int(float(period_el.find('total_maximum').text)),
					)

					moneyline_el = coalesce(period_el, 'moneyline')
					if moneyline_el is not None:
						for vhd in ['home', 'visiting', 'draw']:
							if len(moneyline_el.findall('moneyline_' + vhd)) > 0:
								contestantnum, rotnum = period_el_to_contestantnum_rotnum(period_el, event_el, vhd)
								add_args(
									'odds',
									None,
									eventid = eventid,
									periodnumber = periodnumber,
									snapshotdate = snapshot_sqlite_str,
									type = 'm',
									threshold = 0,
									vhdou = VHDOU_VAL[vhd],
									price = dec_odds(
										coalesce(
											moneyline_el, 'moneyline_' + vhd, 1
										)
									),
									contestantnum = contestantnum,
									rotnum = rotnum,
								)

					spread_el = coalesce(period_el, 'spread')
					if spread_el is not None:
						for vhd in ['home', 'visiting']:
							if len(spread_el.findall('spread_' + vhd)) > 0:
								contestantnum, rotnum = period_el_to_contestantnum_rotnum(period_el, event_el, vhd)
								add_args(
									'odds',
									None,
									eventid = eventid,
									periodnumber = periodnumber,
									snapshotdate = snapshot_sqlite_str,
									type = 's',
									vhdou = VHDOU_VAL[vhd],
									threshold = float(spread_el.find('spread_' + vhd).text),
									price = dec_odds(
										coalesce(
											spread_el, 'spread_adjust_' + vhd, 1
										)
									),
									contestantnum = contestantnum,
									rotnum = rotnum,
								)

					total_el = coalesce(period_el, 'total')
					if total_el is not None:
						for ou in ['over', 'under']:
							contestantnum, rotnum = period_el_to_contestantnum_rotnum(period_el, event_el, ou)
							add_args(
								'odds',
								None,
								eventid = eventid,
								periodnumber = periodnumber,
								snapshotdate = snapshot_sqlite_str,
								type = 't',
								vhdou = VHDOU_VAL[ou],
								threshold = float(total_el.find('total_points').text),
								price = dec_odds(
									coalesce(
										total_el, ou + '_adjust', 1
									)
								),
								contestantnum = contestantnum,
								rotnum = rotnum,
							)

		with get_conn_mysql() as conn:
			LOGGER.info('Queue holds %s queries. Starting execution...', sum(len(al) for al in query_queue.itervalues()))
			for argslist in query_queue.itervalues():
				for args in argslist:
					try:
						if args[0] != AFTER_SQL1 and args[0] != AFTER_SQL2:
							conn.execute(*args)
						else:
							odds_ids = [r[0] for r in conn.execute(args[0], args[1]).fetchall()]
							for odds_id in odds_ids:
								odds_update_sql = '''
									update odds
									set {col} = 1
									where id = %s
								'''.format(col = 'opening' 
										if args[0] == AFTER_SQL1 
										else 'latest')
								conn.execute(odds_update_sql, [odds_id])
					except Exception as e:
						print 'Query that caused exception:'
						print args[0]
						print args[1]
						print
						raise
				conn.commit()
			LOGGER.info('Queue execution done.')
			if self.call_when_update_done is not None:
				self.call_when_update_done(systemdate)


	def to_tree(self, url):
		while True:
			try:
				return etree.parse(urllib2.urlopen(url))
			except IOError as err:
				LOGGER.warning('Retrying later due to error: %s', err)
				time.sleep(self.update_interval)
				continue


	def start(self):

# It's important that systemdate is calculated BEFORE the download
# is started. Otherwise the freshness of the odds will be overestimated,
# leaving room for cheating by users of the beat-the-closing-line game.
		systemdate = datetime.datetime.utcnow()
		last_tree = self.to_tree(STATIC_URL)
		last_download_time = time.time()
		while True:

			self.parse_document(last_tree, systemdate)


			url = (
				STATIC_URL + 
				'lastGame=' + 
				last_tree.find('lastGame').text +
				'&lastContest=' + last_tree.find('lastContest').text
			)

			while True:
				if time.time() > last_download_time + self.update_interval:
					break
				time.sleep(.05)

			LOGGER.info('New url: %s', url)
			last_tree = self.to_tree(url)
			last_download_time = time.time()
			systemdate = datetime.datetime.utcnow()

if __name__ == '__main__':
	parser = argparse.ArgumentParser(
				description = 'Periodically download odds data from the PinnacleSports '
				'feed and save '
				'them to an sqlite database.')
	parser.add_argument('-i', metavar = 'INTERVAL', help = 'How long (in seconds) '
			'to wait between udpates. Pinnacle instructions is to not go below 60. '
			'Default is 120.',
			type = int,
			default = 120)
	args = parser.parse_args()
	UPDATE_INTERVAL = args.i
	### formatter = logging.Formatter(fmt = '%(asctime)s %(levelname)s %(name)s: %(message)s')
	### ROOT_LOGGER.setLevel(logging.DEBUG)
	### if ALSO_TO_STDERR:
	### 	stream_handler = logging.StreamHandler()
	### 	stream_handler.setFormatter(formatter)
	### 	stream_handler.setLevel(logging.DEBUG)
	### rotating_file_handler = logging.handlers.RotatingFileHandler(
	### 		os.path.join(ROOT_DIR, os.path.basename(os.path.abspath(__file__)) + '.log'),
	### 		maxBytes = 10 * 1024 * 1024, 
	### 		backupCount = 2, 
	### 		encoding = 'utf-8'
	### )
	### rotating_file_handler.setFormatter(formatter)
	### rotating_file_handler.setLevel(logging.DEBUG)
	### if ALSO_TO_STDERR:
	### 	ROOT_LOGGER.addHandler(stream_handler)
	### ROOT_LOGGER.addHandler(rotating_file_handler)
	downloader = Downloader(UPDATE_INTERVAL)
	### try:
	### 	downloader.start()
	### except Exception as exc:
	### 	LOGGER.exception('Unhandled exception: \n%s', exc)
	### 	raise

	daemon = daemon.Daemon(
			logpath = os.path.join(ROOT_DIR, 
				os.path.basename(os.path.abspath(__file__)) + '.log'),
			update_interval_seconds = UPDATE_INTERVAL,
			f = downloader.start,
			also_log_to_stderr = ALSO_TO_STDERR,
			level = logging.DEBUG,
			lockid = 'pinnacle_download',
	)

	daemon.start()



