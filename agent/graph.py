from agent.agent import * 

app = StateGraph(AgentState)

app.add_node("tools",ToolNode(tools = TOOLS))
app.add_node("agent",model_call)

app.set_entry_point("agent")
app.add_conditional_edges(
    "agent",
    should_continue_or_not,
    {
        "continue": "tools",
        "end": END  
    }
)
app.add_edge("tools","agent")

graph = app.compile()