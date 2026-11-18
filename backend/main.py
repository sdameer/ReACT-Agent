import os
import json

# fastapi
from fastapi import HTTPException
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/", response_class=HTMLResponse)
def get_ui():
    """Serves the test frontend UI for token streaming."""
    index_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h3>Frontend index.html not found. Place it in the 'frontend' folder.</h3>"


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    # user exists
    user_id = create_user(request.user_name)

    # Check or create convo thread
    thread_id = request.thread_id
    if not thread_id:
        # no prev thread so create one
        thread_id = create_conversation(user_id, title=f"Chat with {request.user_name}")
    else:
        if not conversation_exists(thread_id):
            # when there is an thread but it is invalid 
            raise HTTPException(status_code=404, detail="Conversation thread not found")
    
    history = load_messages(thread_id)
    old_count = len(history)
    
    # combine history with new msg
    messages = history + [HumanMessage(content=request.message)]
    # ------ SSE starts from here ------
    async def event_generator():
        final_messages = []
        try:
            # astream_events v2 yields fine-grained LLM chunks and tool invocations
            async for event in graph.astream_events({"messages": messages}, version="v2"):
                event_type = event["event"]

                # 1. Token chunk from LLM
                if event_type == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if getattr(chunk, "content", None):
                        payload = json.dumps({"type": "token", "content": chunk.content})
                        yield f"data: {payload}\n\n"

                # Agent begins calling a tool 
                elif event_type == "on_tool_start":
                    payload = json.dumps({
                        "type": "tool_start",
                        "tool": event.get("name", "tool"),
                        "input": event["data"].get("input")
                    })
                    yield f"data: {payload}\n\n"

                # Tool execution finished
                elif event_type == "on_tool_end":
                    payload = json.dumps({
                        "type": "tool_end",
                        "tool": event.get("name", "tool"),
                        "output": str(event["data"].get("output"))
                    })
                    yield f"data: {payload}\n\n"

                # Top-level graph completed
                elif event_type == "on_chain_end":
                    out = event["data"].get("output")
                    if isinstance(out, dict) and "messages" in out:
                        if len(out["messages"]) >= len(messages):
                            final_messages = out["messages"]

        except Exception as e:
            payload = json.dumps({"type": "error", "content": str(e)})
            yield f"data: {payload}\n\n"
            return

        # Persist newly generated messages to DB
        if final_messages and len(final_messages) > old_count:
            new_messages = final_messages[old_count:]
            # saving new messages to the thread id
            save_messages(thread_id, new_messages)

        # Signal to client that stream is finished and pass the thread_id
        yield f"data: {json.dumps({'type': 'done', 'thread_id': thread_id})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

