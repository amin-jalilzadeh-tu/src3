# database_utils.py

import psycopg2
import pandas as pd
from config import get_conn_params

conn_params = get_conn_params()

def validate_pc6(pc6_value):
    with psycopg2.connect(conn_params) as conn, conn.cursor() as cursor:
        cursor.execute('SELECT EXISTS(SELECT 1 FROM "TNO_vbobestand" WHERE pc6 = %s)', (pc6_value,))
        return cursor.fetchone()[0]

def fetch_raw_data_for_pc6(pc6_value):
    with psycopg2.connect(conn_params) as conn, conn.cursor() as cursor:
        cursor.execute('SELECT * FROM "TNO_vbobestand" WHERE pc6 = %s', (pc6_value,))
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        return pd.DataFrame(data, columns=columns)

def create_or_replace_table(df, table_name):
    with psycopg2.connect(conn_params) as conn, conn.cursor() as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.commit()

        col_defs = ', '.join(f"{col} TEXT" for col in df.columns)
        cursor.execute(f"CREATE TABLE {table_name} ({col_defs})")
        conn.commit()

        placeholders = ', '.join(['%s'] * len(df.columns))
        insert_query = f"INSERT INTO {table_name} VALUES ({placeholders})"
        for row in df.itertuples(index=False):
            cursor.execute(insert_query, row)
        conn.commit()
