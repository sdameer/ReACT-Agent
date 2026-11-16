from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from agent.graph import graph 

app = FastAPI()


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat(request: ChatRequest):

    res = graph.invoke({
        "messages": [
            HumanMessage(content=request.message)
        ]
    })

    return {
        "response": res["messages"][-1].content
    }