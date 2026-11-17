import os

# fastapi
from fastapi import HTTPException
from fastapi import FastAPI
from contextlib import asynccontextmanager

# agent infra
from typing import Optional
from pydantic import BaseModel
from agent.graph import graph
from langchain_core.messages import HumanMessage

# database :
from database.connect import close_db_pool
from database.connect import get_db_connection
from database.model.memory import init_db
from database.model.user import create_user, create_conversation
from database.helper import load_messages, save_messages, conversation_exists





@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    This function is a lifespan context manager for the FastAPI application.
    
    we have created 10 pool connections to the database
    but it does not close automatically when the server shuts down ,
    so we have to close the pool connections manually when the server shuts down.
    """    
    
    # start
    print("Server starting up...")
    init_db()
    yield
    # shutdown
    print("Server shutting down...")
    close_db_pool()

app = FastAPI(title="ReAct Agent API", lifespan=lifespan)

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
        thread_id = create_conversation(
            user_id, title=f"Chat with {request.user_name}")
    else:
        # FAIL FAST: Validate that the thread exists BEFORE invoking the LLM!
        if not conversation_exists(thread_id):
            raise HTTPException(
                status_code=404, detail="Conversation thread not found")

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



@app.get("/health")
def health_check():
    try:
        # db ping
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        return {"status": "healthy", "database": "connected"}
    
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "database": str(e)}
        )
        