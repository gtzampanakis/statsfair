import time, os, logging, sqlite3, datetime, logging.handlers, collections, urllib2, argparse
import xml.etree.ElementTree as etree
import commonlib as cl

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_URL = 'http://xml.pinnaclesports.com/pinnacleFeed.aspx?'
SECONDS_BETWEEN_ANALYSES = 7 * 24 * 60 * 60 # 7 days
DB_PATH = os.path.join(ROOT_DIR, 'data.db')

BEFORE_SQL = '''
	update odds
	set opening = null, latest = null
	where odds.periodnumber = ?
	and odds.type = ?
	and odds.eventid = ?;
'''
AFTER_SQL1 = '''
	update odds
	set opening = 1
	where odds.periodnumber = ?
	and odds.type = ?
	and odds.eventid = ?
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
	update odds
	set latest = 1
	where odds.periodnumber = ?
	and odds.type = ?
	and odds.eventid = ?
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

def dec_odds(amer_odds):
	if amer_odds is None:
		return None
	amer_odds = float(amer_odds)
	if amer_odds > 0:
		return (100 + amer_odds) / 100.
	else:
		return 100 / (-amer_odds) + 1

def get_conn():
	conn = sqlite3.connect(DB_PATH, timeout = 90.)
	conn.execute('pragma foreign_keys = ON')
	return conn

class Downloader:

	def __init__(self):
		pass


	def make_db(self):
		with get_conn() as conn:
			conn.executescript('''
			create table if not exists events(
				id integer primary key,
				date real not null,
				sporttype text,
				league text,
				islive text,
				description text
			);
			create table if not exists participants(
				eventid integer not null references events(id),
				contestantnum integer not null,
				rotnum integer not null,
				vhdou text,
				name text,
				pitcher text,
				primary key (eventid, contestantnum, rotnum)
			);
			create table if not exists periods(
				eventid integer not null references events(id),
				number integer not null,
				description text not null,
				cutoff real not null,
				scorehome integer,
				scorevisitor integer,
				primary key (eventid, number)
			);
			create table if not exists snapshots(
				eventid integer not null,
				periodnumber integer,
				date real not null,
				status text,
				upd text,
				spreadmax integer,
				mlmax integer,
				totalmax integer,
				primary key (eventid, periodnumber, date),
				foreign key (eventid, periodnumber) references periods(eventid, number)
			);

			create table if not exists odds(
				eventid integer not null,
				periodnumber integer,
				contestantnum integer,
				rotnum integer,
				snapshotdate real not null,
				type text not null,
				vhdou text,
				threshold float,
				price float not null,
				to_base float, -- I have no idea what this is, but keeping it in case it's important and I find out why in the future.

				bookmaker text,

				opening integer,
				latest integer,

				primary key (eventid, periodnumber, snapshotdate, type, vhdou, threshold),
				foreign key (eventid, periodnumber, snapshotdate) references snapshots(eventid, periodnumber, date),
				foreign key (eventid, contestantnum, rotnum) references participants(eventid, contestantnum, rotnum),

				check(price >= 1),

				check(type = 'm' and threshold = 0 or type <> 'm')

			);

			create table if not exists analysis(
				id integer primary key,
				last text not null
			);

			create index if not exists participants1 on participants(eventid, vhdou);
			create index if not exists participants2 on participants(name);
			create index if not exists participants3 on participants(vhdou collate nocase, eventid);
			create index if not exists events1 on events(sporttype, date, id);
			create index if not exists events2 on events(date, id);
			create index if not exists events3 on events(date, islive);
			create index if not exists odds1 on odds(snapshotdate, type);
			create index if not exists odds2 on odds(type);
			create index if not exists periods1 on periods(number);


			create view if not exists gamesdenorm as 
			select
			ev.id as evid,
			ev.date as evdatereal,
			datetime(ev.date) as evdate,
			ev.sporttype as sporttype,
			ev.league as league, 
			ev.islive,
			pah.name as pahnameraw,
			pah.pitcher pahpitcher,
			(case when pah.pitcher is null then pah.name
				else pah.name || ' (' || pah.pitcher || ')' end) as pahname, 
			pav.name pavnameraw,
			pav.pitcher pavpitcher,
			(case when pav.pitcher is null then pav.name
				else pav.name || ' (' || pav.pitcher || ')' end) as pavname, 
			pe.number as penumber,
			pe.description as pedesc,
			odh.threshold as threshold, 
			odh.type as bettype,
			case odh.type when 'm' then 'moneyline'
						when 't' then 'total'
						when 's' then 'spread'
			end as bettypehr,
			odh.price as hprice, 
			odd.price as dprice, 
			odv.price as vprice,
			(case odh.type when 'm' then sn.mlmax
							when 's' then sn.spreadmax
							when 't' then sn.totalmax
			end) as betlimit,
			odh.snapshotdate as snapshotdatereal,
			datetime(odh.snapshotdate) as snapshotdate,
			odh.opening,
			odh.latest,
			odh.rowid as id,
			odh.rowid as hid,
			odd.rowid as did,
			odv.rowid as vid


			from

			events ev
			join participants pah on pah.eventid = ev.id and pah.vhdou = 'Home'
			join participants pav on pav.eventid = ev.id and pav.vhdou = 'Visiting'
			join periods pe on pe.eventid = ev.id
			join odds odh on odh.eventid = ev.id and odh.periodnumber = pe.number 
					and odh.type = odh.type 
					and pah.contestantnum = odh.contestantnum
					and pah.rotnum = odh.rotnum

			join odds odv on odv.eventid = ev.id and odv.periodnumber = pe.number 
					and odv.type = odh.type 
					and pav.contestantnum = odv.contestantnum
					and pav.rotnum = odv.rotnum
					and odv.snapshotdate = odh.snapshotdate

			join snapshots sn on sn.eventid = ev.id and sn.periodnumber = odh.periodnumber
				and sn.date = odh.snapshotdate

			/* The following LEFT JOIN should be after the ODH JOIN
			 * (because it uses values from the above JOIN), but also
			 * needs to be before the ODD join, because the ODD join
			 * uses values from it. */
			left join participants pad on pad.eventid = ev.id and pad.vhdou = 'Draw' and odh.type = 'm'

			left join odds odd on odd.eventid = ev.id 
					and odd.periodnumber = pe.number 
					and odd.type = odh.type 
					and odd.snapshotdate = odh.snapshotdate
					and pad.contestantnum = odd.contestantnum
					and pad.rotnum = odd.rotnum


			/* Sometimes contstantnums change in the same event, and 
			sometimes events are posted with 'Draw' participants but
			without moneyline odds (only spreads and totals are
			posted).  This can lead to cases where Draw odds are
			returned as null by this query, since a 'Draw' participant
			is found but no odds record can be associated with him. The
			following check will avoid those cases. */
			where (pad.rowid is null and odd.rowid is null 
				or 
				pad.rowid is not null and odd.rowid is not null)
			and (case odh.type when 'm' then sn.mlmax
							when 's' then sn.spreadmax
							when 't' then sn.totalmax
			end) > 0
			;

			'''
			)

	def parse_document(self, etree):
		query_queue = collections.defaultdict(list)


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
				args_to_append = cl.get_insert_args(*args, **kwargs)
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
				date = (cl.datetime_to_sqlite_str(evdate_dt), 'julian'),
				sporttype = event_el.find('sporttype').text,
				league = event_el.find('league').text,
				islive = islive,
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
					vhdou = vhd,
					pitcher = pitcher,	
					name = participant_el.find('participant_name').text,
				)
				if is_contest:
					add_args(
						'snapshots',
						'replace',
						eventid = eventid,
						date = (snapshot_sqlite_str, 'julian'),
						mlmax = int(coalesce(event_el, 'contest_maximum', 1)),
					)
					add_args(
						'odds',
						'replace',
						eventid = eventid,
						periodnumber = None,
						snapshotdate = (snapshot_sqlite_str, 'julian'),
						type = 'm',
						threshold = 0,
						vhdou = None,
						price = dec_odds(
							coalesce(
								participant_el, 'odds/moneyline_value', 1
							)
						),
						to_base = coalesce(
									participant_el, 'odds/to_base', 1
						),
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
						cutoff = (period_el.find('periodcutoff_datetimeGMT').text, 'julian'),
					)
					add_args(
						'snapshots',
						'replace', 
						eventid = eventid,
						periodnumber = periodnumber,
						date = (snapshot_sqlite_str, 'julian'),
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
									snapshotdate = (snapshot_sqlite_str, 'julian'),
									type = 'm',
									threshold = 0,
									vhdou = vhd,
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
									snapshotdate = (snapshot_sqlite_str, 'julian'),
									type = 's',
									vhdou = vhd,
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
								snapshotdate = (snapshot_sqlite_str, 'julian'),
								type = 't',
								vhdou = ou,
								threshold = float(total_el.find('total_points').text),
								price = dec_odds(
									coalesce(
										total_el, ou + '_adjust', 1
									)
								),
								contestantnum = contestantnum,
								rotnum = rotnum,
							)

		with get_conn() as conn:
			LOGGER.info('Queue holds %s queries. Starting execution...', sum(len(al) for al in query_queue.itervalues()))
			for argslist in query_queue.itervalues():
				for args in argslist:
					conn.execute(*args)
				conn.commit()
			LOGGER.info('Queue execution done.')
			# Analyze if needed:
			seconds_since_last_analysis = conn.execute("select strftime('%s', current_timestamp) - strftime('%s', analysis.last) from analysis").fetchone()
			seconds_since_last_analysis = seconds_since_last_analysis[0] if seconds_since_last_analysis else None

			LOGGER.info('Seconds since last ANALYZE: %s', seconds_since_last_analysis)
			if seconds_since_last_analysis is None or seconds_since_last_analysis > SECONDS_BETWEEN_ANALYSES:
				LOGGER.info('Running ANALYZE...')
				conn.execute("analyze")
				conn.execute("insert or replace into analysis values (1, current_timestamp)")
				LOGGER.info('ANALYZE done')


	def to_tree(self, url):
		while True:
			try:
				return etree.parse(urllib2.urlopen(url))
			except IOError as err:
				LOGGER.warning('Retrying later due to error: %s', err)
				time.sleep(UPDATE_INTERVAL)
				continue


	def start(self):

		last_tree = self.to_tree(STATIC_URL)
		last_download_time = time.time()
		self.make_db()
		while True:

			self.parse_document(last_tree)


			url = (
				STATIC_URL + 
				'lastGame=' + 
				last_tree.find('lastGame').text +
				'&lastContest=' + last_tree.find('lastContest').text
			)

			while True:
				if time.time() > last_download_time + UPDATE_INTERVAL:
					break
				time.sleep(.05)

			LOGGER.info('New url: %s', url)
			last_tree = self.to_tree(url)
			last_download_time = time.time()

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
	parser.add_argument('DB_PATH', help = 'Path to the database file. '
				'It will be created if it does not exist.')
	args = parser.parse_args()
	DB_PATH = args.DB_PATH
	UPDATE_INTERVAL = args.i
	formatter = logging.Formatter(fmt = '%(asctime)s %(levelname)s %(name)s: %(message)s')
	ROOT_LOGGER.setLevel(logging.DEBUG)
	stream_handler = logging.StreamHandler()
	stream_handler.setFormatter(formatter)
	stream_handler.setLevel(logging.DEBUG)
	rotating_file_handler = logging.handlers.RotatingFileHandler(
			os.path.join(ROOT_DIR, os.path.basename(os.path.abspath(__file__)) + '.log'),
			maxBytes = 10 * 1024 * 1024, 
			backupCount = 2, 
			encoding = 'utf-8'
	)
	rotating_file_handler.setFormatter(formatter)
	rotating_file_handler.setLevel(logging.DEBUG)
	ROOT_LOGGER.addHandler(stream_handler)
	ROOT_LOGGER.addHandler(rotating_file_handler)
	downloader = Downloader()
	try:
		downloader.start()
	except Exception as exc:
		LOGGER.critical('Unhandled exception: %s', exc)
		raise
