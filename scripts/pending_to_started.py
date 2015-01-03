import logging, os, sys, datetime
import cherrypy as cp
import daemon
import statsfair.util as sfutil
import statsfair.pers.sfapp as sfapp

LOGGER = logging.getLogger(__name__)
ROOT_DIR = os.path.dirname(__file__)

def pending_to_started():
	LOGGER.info('Start: pending_to_started')
	with sfutil.get_session('sfapp') as sfapp_sess:
		pending_rows = (
					sfapp_sess
					.query(sfapp.Bet)
					.filter(sfapp.Bet.status == sfapp.Bet.PENDING)
					.order_by(sfapp.Bet.id)
		)
		for pending_bet in pending_rows:
			pending_odds_instance = pending_bet.starting_odds_inst
			LOGGER.info('Handling pending odds with id: %s', pending_odds_instance.id)
# Find candidate odds records, sorted by snapshotdate descending.
			candidate_odds = (
				sfapp_sess
				.query(sfapp.Odds)
				.join(sfapp.Snapshot)
				.join(sfapp.Event)
				.filter(sfapp.Odds.eventid == pending_odds_instance.eventid)
				.filter(sfapp.Odds.periodnumber == pending_odds_instance.periodnumber)
				.filter(sfapp.Odds.contestantnum == pending_odds_instance.contestantnum)
				.filter(sfapp.Odds.type == pending_odds_instance.type)
				.filter(sfapp.Odds.vhdou == pending_odds_instance.vhdou)
				.filter(sfapp.Odds.snapshotdate > pending_odds_instance.snapshotdate)
				.filter(sfapp.Odds.snapshotdate <= sfapp.Event.date)
				.filter(sfapp.Snapshot.mlmax > 0)
				.order_by(sfapp.Odds.snapshotdate)
			)
			for candidate_odd in candidate_odds:
				LOGGER.info('Candidate odd: %s', candidate_odd.id)
				diff_in_seconds = (candidate_odd.snapshotdate 
									- pending_bet.placedat).total_seconds()
				LOGGER.info('Difference is %s seconds', diff_in_seconds)
				if diff_in_seconds < sfutil.PENDING_LIFESPAN:
					LOGGER.info('New starting_odds_inst for bet %s', pending_bet)
					pending_bet.starting_odds_inst = candidate_odd
			# The starting_odds_inst has possibly changed, so the stakes might
			# need to be changed as well.
			excess_stake = pending_bet.stake - pending_bet.starting_odds_inst.snapshot.mlmax
			LOGGER.info('Excess stake: %s', excess_stake)
			if excess_stake > 0:
				LOGGER.info('Odds change resulted in excess_stake of %s', excess_stake)
				pending_bet.stake = pending_bet.starting_odds_inst.snapshot.mlmax
				transaction = sfapp.Transaction(
						userid = pending_bet.userid,
						amount = excess_stake,
						date = datetime.datetime.utcnow(),
						description = sfapp.Transaction.EXCESS_STAKE_CORRECTION
				)
				sfapp_sess.add(transaction)
			diff = (datetime.datetime.utcnow()
						- pending_bet.placedat).total_seconds()
			LOGGER.info('Diff is %s seconds', diff)
			if diff >= sfutil.PENDING_LIFESPAN:
				LOGGER.info('Changing bet %s to STARTED', pending_bet)
				pending_bet.status = sfapp.Bet.STARTED
		
	LOGGER.info('End: pending_to_started')

if __name__ == '__main__':

	daemon = daemon.Daemon(
			logpath = os.path.join(ROOT_DIR, sys.argv[0] + '.log'),
			update_interval_seconds = 10.,
			f = pending_to_started,
			level = logging.DEBUG,
			also_log_to_stderr = 1)

	daemon.start()


