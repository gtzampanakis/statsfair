import logging
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, Column, Integer, String, DateTime, TIMESTAMP, func


Base = declarative_base()

class User(Base):
	__tablename__ = 'users'

	id = Column(Integer, primary_key = True)
	username = Column(String(50), unique = True, nullable = False)
	pwhash = Column(String(120), nullable = False)
	reccreatedat = Column(DateTime, default = func.utc_timestamp())
	recupdatedat = Column(DateTime, default = func.utc_timestamp(), 
										onupdate = func.utc_timestamp())


if __name__ == '__main__':
	logging.basicConfig(level = logging.DEBUG)
	connection_string = r'mysql+mysqldb://root:root@localhost/sfapp?charset=utf8&use_unicode=0'
	engine = create_engine(connection_string, echo = True)
	Session = sessionmaker(bind = engine)
	session = Session
	Base.metadata.create_all(engine)

	print session

