from psycopg2.extras import Json
from fastapi import HTTPException

from langchain_core.messages import (
    message_to_dict,
    messages_from_dict
)

from database.connect import get_db_connection


# Load previous messages
def load_messages(thread_id):

    with get_db_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT m.content
                FROM messages m
                JOIN conversations c
                ON m.conversation_id = c.id
                WHERE c.thread_id = %s
                ORDER BY m.id;
            """, (thread_id,))

            rows = cur.fetchall()

    message_data = [row[0] for row in rows]

    return messages_from_dict(message_data)


# Save new messages
def save_messages(thread_id, messages):

    if not messages:
        return

    with get_db_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT id FROM conversations
                WHERE thread_id = %s;
            """, (thread_id,))

            result = cur.fetchone()

            if result is None:
                # raise ValueError("Conversation not found")
                raise HTTPException(status_code=404, detail="Conversation not found")

            conversation_id = result[0]

            for message in messages:

                cur.execute("""
                    INSERT INTO messages
                    (conversation_id, message_type, content)
                    VALUES (%s, %s, %s);
                """, (
                    conversation_id,
                    message.type,
                    Json(message_to_dict(message))
                ))

            cur.execute("""
                UPDATE conversations
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            """, (conversation_id,))
            
            
            
def conversation_exists(thread_id: str) -> bool:
    """
    before running the agent we are running this function to check
    if the conversation exists in the database or not    
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM conversations WHERE thread_id = %s;", (thread_id,))
            return cur.fetchone() is not None            