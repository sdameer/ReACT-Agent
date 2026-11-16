from agent.graph import graph
from langchain_core.messages import HumanMessage

if __name__ == "__main__":
    res = graph.invoke({
        "messages":[
            HumanMessage(content="add 1 and 2 then multiply with 2 subtract with 2 and then add -2"),
        ]
    })
    for msg in res['messages']:
        print(f"{msg.__class__.__name__} : {msg.content}")
    


