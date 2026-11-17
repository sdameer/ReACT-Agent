import os
import psycopg2
from contextlib import contextmanager
from dotenv import load_dotenv
from psycopg2.pool import ThreadedConnectionPool
# opening and closing the db connections take very long time so we use a connection pool
# to reuse existing connections instead of creating new ones for every request

load_dotenv()

# create the pool ONCE with 1 to 10 reusable connections
db_pool = ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    dbname=os.getenv("DB_NAME"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)


# this @contextmanager decorator allows us to use the function as a context manager,
# use it with the 'with' statement to automatically handle opening and closing the 
# database connection.
@contextmanager
def get_db_connection():
    # get a connection from the pool
    conn = db_pool.getconn()
    
    try:
        yield conn
        conn.commit()
        
    except Exception:
    # in case of an error , rollback 
    # dont save any changes made during the transaction
        conn.rollback()
        raise
    
    finally:
        # return the connection back to the pool for the next request
        db_pool.putconn(conn)        