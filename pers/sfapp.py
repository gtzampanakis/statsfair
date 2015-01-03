import logging
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, ForeignKeyConstraint, Float, Numeric, func
from sqlalchemy.dialects.mysql import MEDIUMINT, INTEGER


Base = declarative_base()

class User(Base):
	__tablename__ = 'users'

	id = Column(Integer, primary_key = True)
	username = Column(String(50), unique = True, nullable = False)
	pwhash = Column(String(120), nullable = False)
	reccreatedat = Column(DateTime, default = func.utc_timestamp())
	recupdatedat = Column(DateTime, default = func.utc_timestamp(), 
										onupdate = func.utc_timestamp())

class Event(Base):
	__tablename__ = 'events'
	__table_args__ = {'schema' : 'pinn'}

	id = Column(Integer, primary_key = True)
	date = Column(DateTime)
	sporttype = Column(String)
	league = Column(String)
	islive = Column(Integer)
	description = Column(String)

class Participant(Base):
	__tablename__ = 'participants'
	__table_args__ = {'schema' : 'pinn'}

	id = Column(Integer, primary_key = True)
	eventid = Column(Integer, ForeignKey('pinn.events.id'))
	contestantnum = Column(Integer)
	vhdou = Column(String)
	name = Column(String)
	pitcher = Column(String)

	event = relationship(Event, backref = backref('participants', order_by = id))

class Snapshot(Base):
	__tablename__ = 'snapshots'
	__table_args__ = {'schema' : 'pinn'}

	id = Column(Integer, primary_key = True)
	eventid = Column(Integer, ForeignKey('pinn.events.id'))
	periodnumber = Column(Integer)
	date = Column(DateTime)
	mlmax = Column(Integer)
	event = relationship(Event, backref = backref('snapshots'))

class Odds(Base):
	__tablename__ = 'odds'

	id = Column(Integer, primary_key = True)
	eventid = Column(Integer, ForeignKey('pinn.events.id'))
	periodnumber = Column(Integer)
	contestantnum = Column(Integer)
	snapshotdate = Column(DateTime)
	type = Column(String)
	vhdou = Column(String)
	price = Column(Float)

	event = relationship(Event, backref = backref('odds_list'))
	participant = relationship(Participant, backref = backref('odds_list'))
	snapshot = relationship(Snapshot, backref = backref('odds_list'))

	__table_args__ = (ForeignKeyConstraint([eventid, contestantnum], 
							[Participant.eventid, Participant.contestantnum]), 
						ForeignKeyConstraint([eventid, periodnumber, snapshotdate], 
						[Snapshot.eventid, Snapshot.periodnumber, Snapshot.date]),
							{'schema' : 'pinn'})


class Bet(Base):
	__tablename__ = 'bets'

	PENDING = 'P'
	STARTED = 'S'
	SETTLED = 'T'

	id = Column(Integer, primary_key = True)
	userid = Column(Integer, ForeignKey('users.id'), nullable = False, primary_key = True)
	starting_oddsid = Column(INTEGER(unsigned = True), ForeignKey('pinn.odds.id'))
	settled_oddsid = Column(INTEGER(unsigned = True), ForeignKey('pinn.odds.id'))
	stake = Column(Numeric(8, 2), nullable = False)
	duration = Column(Integer)
	status = Column(String(2), nullable = False)
	placedat = Column(DateTime, nullable = False)
	settledat = Column(DateTime)

	reccreatedat = Column(DateTime, default = func.utc_timestamp())
	recupdatedat = Column(DateTime, default = func.utc_timestamp(), 
										onupdate = func.utc_timestamp())

	user = relationship(User)
	starting_odds_inst = relationship(Odds, foreign_keys = starting_oddsid, 
										backref = backref('bets_starting', order_by = id))
	settled_odds_inst = relationship(Odds,  foreign_keys = settled_oddsid, 
										backref = backref('bets_settled', order_by = id))

class InitBalance(Base):
	__tablename__ = 'initbalances'

	userid = Column(Integer, ForeignKey('users.id'), nullable = False, primary_key = True)
	balance = Column(Numeric(4, 0), nullable = False)

	reccreatedat = Column(DateTime, default = func.utc_timestamp())
	recupdatedat = Column(DateTime, default = func.utc_timestamp(), 
										onupdate = func.utc_timestamp())

	user = relationship(User)

class Transaction(Base):
	__tablename__ = 'transactions'

	EXCESS_STAKE_CORRECTION = 'EXCESS_STAKE_CORRECTION'
	BET_SUBMIT_STAKE = 'BET_SUBMIT_STAKE'
	BET_SETTLE_RETURN_STAKE = 'BET_SETTLE_RETURN_STAKE'
	BET_SETTLE_YIELD = 'BET_SETTLE_YIELD'

	id = Column(Integer, primary_key = True)
	userid = Column(Integer, ForeignKey('users.id'), nullable = False)
	amount = Column(Numeric(8, 2), nullable = False)
	date = Column(DateTime, nullable = False)
	description = Column(String(100))

	reccreatedat = Column(DateTime, default = func.utc_timestamp())
	recupdatedat = Column(DateTime, default = func.utc_timestamp(), 
										onupdate = func.utc_timestamp())

	user = relationship(User, backref = backref('transactions'))





if __name__ == '__main__':
	logging.basicConfig(level = logging.DEBUG)
	connection_string = r'mysql+mysqldb://root:root@localhost/sfapp?charset=utf8&use_unicode=0'
	engine = create_engine(connection_string, echo = True)
	Session = sessionmaker(bind = engine)
	Base.metadata.create_all(engine)

	session = Session()
	print session.query(Event).filter_by(id = 	318588048).one().league

	print session.query(Participant).filter_by(contestantnum = 1853).first().event.league

	print session.query(Odds).filter_by(id = 1).first().event.date

