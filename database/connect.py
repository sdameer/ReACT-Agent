import os
import psycopg2

from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

# this @contextmanager decorator allows us to use the function as a context manager,
# use it with the 'with' statement to automatically handle opening and closing the 
# database connection.
@contextmanager
def get_db_connection():

    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    try:
        yield conn
        conn.commit()

    except Exception:
    # in case of an error , rollback 
    # dont save any changes made during the transaction
        conn.rollback()
        raise

    finally:
        conn.close()