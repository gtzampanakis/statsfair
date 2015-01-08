import logging, os, sys, datetime
import cherrypy as cp
import daemon
import statsfair.util as sfutil
import statsfair.pers.sfapp as sfapp

LOGGER = logging.getLogger(__name__)
ROOT_DIR = os.path.dirname(__file__)

def started_to_settled():
	LOGGER.info('Start: started_to_settled')
	with sfutil.get_session('sfapp') as sfapp_sess:
		started_rows = (
					sfapp_sess
					.query(sfapp.Bet)
					.filter(sfapp.Bet.status == sfapp.Bet.STARTED)
					.order_by(sfapp.Bet.id)
		)
		for started_bet in started_rows:
			if started_bet.settled_odds_inst is None:
				started_bet.settled_odds_inst = started_bet.starting_odds_inst
			started_odds_instance = started_bet.settled_odds_inst
			LOGGER.info('Handling started odds with id: %s', started_odds_instance.id)
# Find candidate odds records, sorted by snapshotdate descending.
			candidate_odds = (
				sfapp_sess
				.query(sfapp.Odds)
				.join(sfapp.Snapshot)
				.join(sfapp.Event)
				.filter(sfapp.Odds.eventid == started_odds_instance.eventid)
				.filter(sfapp.Odds.periodnumber == started_odds_instance.periodnumber)
				.filter(sfapp.Odds.contestantnum == started_odds_instance.contestantnum)
				.filter(sfapp.Odds.type == started_odds_instance.type)
				.filter(sfapp.Odds.vhdou == started_odds_instance.vhdou)
				.filter(sfapp.Odds.snapshotdate > started_odds_instance.snapshotdate)
				.filter(sfapp.Odds.snapshotdate <= sfapp.Event.date)
				.filter(sfapp.Snapshot.mlmax > 0)
				.order_by(sfapp.Odds.snapshotdate)
			)
			for candidate_odd in candidate_odds:
				LOGGER.info('Candidate odd: %s', candidate_odd.id)
				LOGGER.info('New settled_oddsid for bet %s', started_bet)
				started_bet.settled_odds_inst = candidate_odd
			# The settled_odds_inst has possibly changed, so the stakes might
			# need to be changed as well.
			if started_bet.settled_odds_inst:
				excess_stake = started_bet.stake - started_bet.settled_odds_inst.snapshot.mlmax
				LOGGER.info('Excess stake: %s', excess_stake)
				if excess_stake > 0:
					LOGGER.info('Odds change resulted in excess_stake of %s', excess_stake)
					started_bet.stake = started_bet.settled_odds_inst.snapshot.mlmax
					transaction = sfapp.Transaction(
							userid = started_bet.userid,
							amount = excess_stake,
							date = datetime.datetime.utcnow(),
							description = sfapp.Transaction.EXCESS_STAKE_CORRECTION,
					)
					sfapp_sess.add(transaction)
			diff = (datetime.datetime.utcnow()
						- started_bet.starting_odds_inst.event.date).total_seconds()
			LOGGER.info('Now: %s, evdate: %s', datetime.datetime.utcnow(), 
									started_bet.starting_odds_inst.event.date)
			LOGGER.info('Diff is %s seconds', diff)
			if diff >= sfutil.SAFETY_WAIT_PERIOD:
				LOGGER.info('Changing bet %s to SETTLED', started_bet)
				started_bet.status = sfapp.Bet.SETTLED
				start_price = started_bet.starting_odds_inst.price
				end_price = started_bet.settled_odds_inst.price
				LOGGER.info('Bet settled; start_price: %s, end_price: %s',
								start_price, end_price)
				factor = start_price / end_price - 1.
				change = float(started_bet.stake) * factor
				transaction_return = sfapp.Transaction(
						userid = started_bet.userid,
						amount = started_bet.stake,
						date = datetime.datetime.utcnow(),
						description = sfapp.Transaction.BET_SETTLE_RETURN_STAKE,
				)
				transaction_change = sfapp.Transaction(
						userid = started_bet.userid,
						amount = change,
						date = datetime.datetime.utcnow(),
						description = sfapp.Transaction.BET_SETTLE_YIELD,
				)
				sfapp_sess.add(transaction_return)
				sfapp_sess.add(transaction_change)
		
	LOGGER.info('End: started_to_settled')

if __name__ == '__main__':

	daemon = daemon.Daemon(
			logpath = os.path.join(ROOT_DIR, sys.argv[0] + '.log'),
			update_interval_seconds = 10.,
			f = started_to_settled,
			level = logging.DEBUG,
			also_log_to_stderr = 1)

	daemon.start()


