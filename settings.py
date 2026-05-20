import datetime
from db import create_db_conn

def database_refresh_timestamp(conn=None):
    if conn is None:
        conn=create_db_conn()
        close_after = True
    else:
        close_after = False

    try:
        cursor = conn.cursor()

        # check if table exists
        cursor.execute("""SELECT to_regclass('public.app_metadata') IS NOT NULL;
                       """
                        )
        metadata_exists = cursor.fetchone()[0]

        # create app_metadata table if it doesn't exist
        if not metadata_exists:
            cursor.execute("""
            CREATE TABLE app_metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """)
            conn.commit()

        # get last database refresh timestamp
        cursor.execute("SELECT value FROM app_metadata WHERE key = 'last_refresh';")
        row = cursor.fetchone()

        # if database has never been updated need to tell UI to show that
        if row is None:
            return None
        
        # if database has been updated before return the last recorded timestamp
        return datetime.datetime.fromisoformat(row[0]).astimezone()

    finally:
        cursor.close()
        if close_after:
            conn.close()


def save_refresh_timestamp(conn=None):
    if conn is None:
        conn = create_db_conn()
        close_after = True
    else:
        close_after = False

    try:
        cursor = conn.cursor()
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() # get current time in UTC format
        # update last_refresh timestamp in app_metadata table
        cursor.execute("""
            INSERT INTO app_metadata (key, value)
            VALUES ('last_refresh', %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
        """, (timestamp,))
        conn.commit()

    finally:
        cursor.close()
        if close_after:
            conn.close()
