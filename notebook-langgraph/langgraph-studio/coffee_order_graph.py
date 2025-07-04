from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from typing import Literal
import random

class State(TypedDict):
    order_state: str

def take_order(state):
    print("📝 Taking customer order")
    state["order_state"] = "Customer wants coffee"
    return state

def add_milk(state):
    print("🥛 Adding milk to coffee")
    state["order_state"] = "Coffee with milk prepared"
    return state

def add_sugar(state):
    print("🧂 Adding sugar to coffee")
    state["order_state"] = "Coffee with sugar prepared"
    return state

def serve_order(state):
    print("☕ Serving the coffee")
    state["order_state"] = "Order completed"
    return state

def customization_choice(state) -> Literal["add_milk", "add_sugar"]:
    # Randomly choose between milk or sugar
    if random.random() > 0.5:
        return "add_milk"
    else:
        return "add_sugar"

# Create the graph
builder = StateGraph(State)

# Add nodes
builder.add_node("take_order", take_order)
builder.add_node("add_milk", add_milk)
builder.add_node("add_sugar", add_sugar)
builder.add_node("serve_order", serve_order)

# Add edges
builder.add_edge(START, "take_order")
builder.add_conditional_edges("take_order", customization_choice)
builder.add_edge("add_milk", "serve_order")
builder.add_edge("add_sugar", "serve_order")
builder.add_edge("serve_order", END)

# Compile the graph
graph = builder.compile()

# # Run the graph
# result = graph.invoke({"order_state": ""})
# print(f"\nFinal state: {result['order_state']}") 