import contextlib, logging, time, datetime

logger = logging.getLogger(__name__)

class Connection:

	def __init__(self, dbapi_conn):
		self.dbapi_conn = dbapi_conn

	def execute(self, sql, params = [ ], convert_dates = True):
		logger.debug('Starting execution of query: %s', sql)
		logger.debug('Parameters for last query: %s', params)

		t0 = time.time()
		cursor = self.dbapi_conn.cursor()

		if convert_dates:
			conv_params = [ ]
			for el in params:
				if isinstance(el, datetime.date) or isinstance(el, datetime.datetime):
					conv_params.append(
						'/'.join([
							str(el.year).zfill(4),
							str(el.month).zfill(2),
							str(el.day).zfill(2),
						])
					)
				else:
					conv_params.append(el)
			params = conv_params
			logger.debug('Parameters for last query (after date conversion): %s', params)

		cursor.execute(sql, params)
		t1 = time.time()

		logger.debug('Query execution took %.3f seconds', t1 - t0)

		return cursor

	def explain(self, sql, params = [ ]):
		return self.execute('explain ' + sql, params)

	def close(self):
		return self.dbapi_conn.close()

	def commit(self):
		return self.dbapi_conn.commit()

	def rollback(self):
		return self.dbapi_conn.rollback()


@contextlib.contextmanager
def connect(dbapi_conn_construct_callable):
	""" 
	dbapi_conn_construct_callable should be a callable 
	that accepts no arguments and returns a DB API connection
	"""
	conn = None
	try:
		conn = Connection(dbapi_conn_construct_callable())
		yield conn
	except Exception as e:
		if conn is not None:
			conn.rollback()
		raise e
	else:
		conn.commit()
	finally:
		if conn is not None:
			conn.close()

if __name__ == '__main__':
	import sqlite3
	logging.basicConfig(level = logging.DEBUG)
	with connect(lambda: sqlite3.connect(':memory:')) as conn:
		conn.execute('create table foo(bar integer)');
		conn.execute('insert into foo (bar) values (1)')
		conn.execute('insert into foo (bar) values (2)')
		conn.execute('insert into foo (bar) values (3)')
		conn.execute('insert into foo (bar) values (4)')
		conn.execute('insert into foo (bar) values (5)')
		for row in conn.execute('select * from foo'):
			print row
