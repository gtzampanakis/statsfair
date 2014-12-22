import logging, datetime

LOGGER = logging.getLogger(__name__)

def get_insert_args(table, on_conflict = None, **kwargs):

	def is_j(v):
		return (isinstance(v, tuple) or isinstance(v, list)) and v[1] == 'julian'

	sql = '''
		insert {conflict} into {table}
		({names})
		values
		({question_marks})
		'''
	names = [ ]
	values = [ ]
	for name, value in kwargs.iteritems():
		names.append(name)
		if hasattr(value, 'year') and hasattr(value, 'month') and hasattr(value, 'day'):
			value = date_to_sqlite_str(value)
		values.append(value)
	sql = sql.format(
			table = table,
			names = ', '.join(names),
			question_marks = ', '.join(
				('julianday(?)' if is_j(v) else '?')
				for v in values
			),
			conflict = '' if on_conflict is None else 'or ' + on_conflict,
	)
	values = [v if not is_j(v) else v[0] for v in values]
	LOGGER.debug('get_insert_args sql: %s, args: %s', sql, values)
	return sql, values

def datetime_to_sqlite_str(dt):
	return datetime.datetime.strftime(
		dt, '%Y-%m-%d %H:%M'
	)
