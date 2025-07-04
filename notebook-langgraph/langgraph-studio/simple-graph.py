from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    
    graph_state: str
from typing import Literal
import random

def node1(state):
    print("Passing by node 1")
    state["graph_state"] = "Lucas loves Elmo"
    return state

def node2(state):
    print("Passing by node 2")
    state["graph_state"] = "Lucas loves Pancakes" 
    return state

def node3(state):
    print("Passing by node 3")
    state["graph_state"] = "Lucas loves students that ask awesome questions"
    return state

def decision_node(state) -> Literal["node2", "node3"]:
    
    user_input = state["graph_state"]
    
    if random.random() > 0.5:
        return "node2"
    else:
        return "node3"
builder = StateGraph(State)

builder.add_node("node1", node1)
builder.add_node("node2", node2)
builder.add_node("node3", node3)

builder.add_edge(START, "node1")
builder.add_conditional_edges("node1",decision_node)
builder.add_edge("node2", END)
builder.add_edge("node3", END)

graph = builder.compile()