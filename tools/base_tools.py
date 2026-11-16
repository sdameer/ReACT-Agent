from langchain_core.tools import tool

@tool
def add(x : int , y : int) -> int:
    """Add two numbers."""
    return x + y

@tool
def subtract(x : int , y : int) -> int:
    """Subtract two numbers."""
    return x - y    

@tool
def multiply(x : int , y : int) -> int:
    """Multiply two numbers."""
    return x * y    


TOOLS = [add, subtract, multiply]
