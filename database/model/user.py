from uuid import uuid4

from database.connect import get_db_connection


def create_user(username):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (username)
                VALUES (%s)
                ON CONFLICT (username)
                DO UPDATE SET username = EXCLUDED.username
                RETURNING id;
            """ , (username,))

            return cur.fetchone()[0]


def create_conversation(user_id, title="New Chat"):
    thread_id = str(uuid4())

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO conversations (user_id, thread_id, title)
                VALUES (%s, %s, %s)
                RETURNING thread_id;
            """, (user_id, thread_id, title))

            return str(cur.fetchone()[0])