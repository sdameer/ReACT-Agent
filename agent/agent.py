from typing import TypedDict, Union, List, Annotated, Sequence

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage

from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END

from tools.base_tools import TOOLS
from prompts.base import BASE_PROMPT

from dotenv import load_dotenv
import os 
load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

class AgentState(TypedDict):
    """A dictionary representing the state of the agent."""
    messages: Annotated[List[BaseMessage], add_messages]
    
    
model = ChatGroq(model="openai/gpt-oss-120b",temperature=0)
model = model.bind_tools(tools = TOOLS)
    
    
def model_call(state: AgentState):
    response = model.invoke(
        [
            SystemMessage(content=BASE_PROMPT),
            *state["messages"],
        ]
    )
    return {"messages": [response]}



def should_continue_or_not(state : AgentState) :
    """Determine whether the agent should continue or stop."""
    
    messages = state["messages"]    
    if not messages[-1].tool_calls:        
        return "end"
    return "continue"
        
        
        