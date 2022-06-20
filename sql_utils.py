import os

import pymysql

from credentials import secrets
from constants import *

dev = os.getenv('PRODUCTION') != 'true'

sql_host = secrets['sql_host'] if dev else 'mysql'

config = {'host': sql_host, 'user': secrets['sql_user'], 'password': secrets['sql_password'], 'db': APP_NAME, 'autocommit': True, 'port': secrets['sql_port'],
          'cursorclass': pymysql.cursors.DictCursor}


def sql_req(query, *params, fetch_one=False, fetch_all=False, last_row_id=False):
    conn = pymysql.connect(**config)
    cur = conn.cursor()
    cur.execute(query, params)
    if fetch_one:
        return cur.fetchone()
    elif fetch_all:
        return cur.fetchall()
    elif last_row_id:
        return cur.lastrowid


def sql_insert(table, last_row_id=False, **values):
    table = f'`{table}`'
    keys = ', '.join([key for key in values.keys()])
    filler = ', '.join(['%s'] * len(values.keys()))
    return sql_req(f'INSERT INTO {table} ({keys}) VALUES ({filler})', *values.values(), last_row_id=last_row_id)
