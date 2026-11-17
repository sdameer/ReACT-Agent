
from database.model.memory import init_db
from database.model.user import create_user, create_conversation
from backend.main import chat

init_db()

user_id = create_user("ameer")

thread_id = create_conversation(user_id)

print("Thread ID:", thread_id)

response = chat(thread_id, "Hi, introduce yourself.")

print("Agent:", response)
