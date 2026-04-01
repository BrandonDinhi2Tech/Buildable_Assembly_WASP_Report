import psycopg2

def create_db_conn():
    cnx = psycopg2.connect(
        user='postgres', 
        password='711268', 
        host='127.0.0.1',
        port='5432',
        database='buildable_assembly_wasp', 
    )
    return cnx