
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from agent.graph import graph
from database.model.memory import init_db
from database.model.user import create_user, create_conversation
from database.helper import load_messages, save_messages

app = FastAPI()

# Initialize database and create a conversation
init_db()

user_id = create_user("ameer")
thread_id = create_conversation(user_id, "First Chat")


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat(request: ChatRequest):

    # Load previous messages
    history = load_messages(thread_id)
    old_count = len(history)

    # Add new user message
    messages = history + [HumanMessage(content=request.message)]

    # Invoke agent
    res = graph.invoke({"messages": messages})

    # Save only new messages
    new_messages = res["messages"][old_count:]
    save_messages(thread_id, new_messages)

    return {
        "response": res["messages"][-1].content,
        "thread_id": thread_id
    }
