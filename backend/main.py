from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from agent.graph import graph
from database.model.memory import init_db
from database.model.user import create_user, create_conversation
from database.helper import load_messages, save_messages ,conversation_exists
from fastapi import HTTPException

app = FastAPI(title="ReAct Agent API")

# Initialize database tables on server startup (similar to running migrations)
init_db()


class ChatRequest(BaseModel):
    message: str
    user_name: str = "ameer"
    thread_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    thread_id: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    #  user exists or user_id
    user_id = create_user(request.user_name)

    # new conversation or an existing one
    thread_id = request.thread_id
    if not thread_id:
        thread_id = create_conversation(user_id, title=f"Chat with {request.user_name}")
    else:
        # FAIL FAST: Validate that the thread exists BEFORE invoking the LLM!
        if not conversation_exists(thread_id):
            raise HTTPException(status_code=404, detail="Conversation thread not found")

    # history
    history = load_messages(thread_id)
    old_count = len(history)

    messages = history + [HumanMessage(content=request.message)]

    # Run agent
    res = await graph.ainvoke({"messages": messages})
    
    # Append to db 
    new_messages = res["messages"][old_count:]
    save_messages(thread_id, new_messages)
    
    return {
        "response": res["messages"][-1].content,
        "thread_id": thread_id
    }