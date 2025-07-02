import marimo

__generated_with = "0.14.7"
app = marimo.App()


@app.cell
def mmports_and_setup():
    # Cell 1: Imports and Setup
    import marimo as mo
    import quarto as qt
    import os
    import getpass
    from typing_extensions import TypedDict
    from typing import Literal
    import random
    from langgraph.graph import StateGraph, START, END
    import base64

    mo.md("# Imports and Setup")
    return END, Literal, START, StateGraph, TypedDict, base64, getpass, mo, os


@app.cell
def _(getpass, mo, os):
    # Cell 2: Environment Setup
    def _set_env(var: str):
        if not os.environ.get(var):
            os.environ[var] = getpass.getpass(f"{var}: ")

    _set_env("OPENAI_API_KEY")

    mo.md("# Environment Setup get API Key")
    return


@app.cell
def _(mo):
    mo.md(
        """
    # 🚀 Practical Introduction to LangGraph

    ## This notebook provides a hands-on introduction to LangGraph fundamentals:
    - **States**: Data structures that get updated during graph execution
    - **Nodes**: Functions that transform state data
    - **Edges**: Connections between nodes (direct or conditional)
    - **Graphs**: Complete workflows that combine everything together

    ## 📦 Installation & Dependencies

    Let's start by installing the required packages and setting up our environment.

    ## 🔑 API Key Configuration

    We'll load API keys from a `.env` file for secure credential management.
    Create a `.env` file in your project root with:

    ```env
    OPENAI_API_KEY=your_openai_api_key_here
    ANTHROPIC_API_KEY=your_anthropic_api_key_here
    ```
    """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.vstack([
        mo.md("# States"),
        mo.md(" "),
        mo.md("## Data structure that get's updated when we execute a graph."),
        mo.md(" "),
        mo.md("# Nodes"),
        mo.md(" "),
        mo.md("## Functions where we perform updates to states by adding or transforming the keys of that state."),
        mo.md(" "),
        mo.md("# Edges"),
        mo.md(" "),
        mo.md("## Connect the nodes together (they can be direct a->b or conditional a->b or a->c)."),
        mo.md(" "),
        mo.md("# Graph (build & invoke)"),
        mo.md("The [DAG cycle](https://en.wikipedia.org/wiki/Directed_acyclic_graph) that combines the entire thing.")
    ])
    return


@app.cell
def _(mo):
    # Cell 5: Setup Instructions
    mo.vstack([
        mo.md("## 📦 Setup & Dependencies"),
        mo.md("This notebook requires a properly set up environment with uv. Before running:"),
        mo.md("1. **Install uv**: Follow instructions at [docs.astral.sh/uv](https://docs.astral.sh/uv/)"),
        mo.md("2. **Sync dependencies**: Run `uv sync` from the project root"),
        mo.md("3. **Use correct kernel**: Ensure your Jupyter kernel uses the uv environment"),
        mo.md("All required packages are managed via the project's `pyproject.toml`.")
    ])
    return


@app.cell
def _(mo):
    # Cell 6: Simple State Section Header
    mo.vstack([
        mo.md("# State"),
        mo.md("State as a simple data structure that we update as we execute the graph.")
    ])

    return


@app.cell
def _(TypedDict):
    # Cell 7: Define Simple State and Node
    class State(TypedDict):    
        state_before_node1: str
        state_after_node1: str

    def node1(state):
        print("Passing by node 1")
        state["state_after_node1"] = "Passed by node1"
        return state

    return State, node1


@app.cell
def _(END, START, State, StateGraph, node1):
    # Cell 8: Build Simple Graph
    builder = StateGraph(State)
    builder.add_node("node1", node1)
    builder.add_edge(START, "node1")
    builder.add_edge("node1", END)
    simple_graph = builder.compile()

    return (simple_graph,)


@app.cell
def _(mo, simple_graph):
    # Cell 9: Test Simple Graph
    result1 = simple_graph.invoke({"state_before_node1": "This is node 1! Lucas loves pancakes!"})
    mo.md(f"**First Graph Result:**\n```python\n{result1}\n```")


    return


@app.cell
def _(mo):
    # Cell 10: Routing Section Header
    mo.md("# Routing")

    return


@app.cell
def _(END, Literal, START, StateGraph, TypedDict):
    # Cell 11: Define Routing Components and Build Graph
    def node1_routing(state):
        print("Passing by node 1")
        return state

    def node2(state):
        print("Passing by node 2")
        state["graph_state"] = "node 2" 
        return state

    def node3(state):
        print("Passing by node 3")
        state["graph_state"] = "node 3"
        return state

    def decision_node(state) -> Literal["node2", "node3"]:
        user_input = state["graph_state"]
        print(user_input)
    
        if user_input == "2":
            return "node2"
        else:
            return "node3"

    class RoutingState(TypedDict):
        graph_state: str

    routing_builder = StateGraph(RoutingState)
    routing_builder.add_node("node1", node1_routing)
    routing_builder.add_node("node2", node2)
    routing_builder.add_node("node3", node3)
    routing_builder.add_edge(START, "node1")
    routing_builder.add_conditional_edges("node1", decision_node)
    routing_builder.add_edge("node2", END)
    routing_builder.add_edge("node3", END)
    routing_graph = routing_builder.compile()

    return (routing_graph,)


@app.cell
def _(base64, mo):
    # Cell 12: Graph Visualization Function
    def display_graph_image(graph):
        """Display the graph visualization in marimo"""
        try:
            # Get the mermaid PNG bytes
            png_bytes = graph.get_graph().draw_mermaid_png()
        
            # Convert to base64 for display
            img_base64 = base64.b64encode(png_bytes).decode()
        
            # Create HTML img tag
            html_content = f'<img src="data:image/png;base64,{img_base64}" alt="Graph Visualization" style="max-width: 100%; height: auto;">'
        
            return mo.Html(html_content)
        except Exception as e:
            return mo.md(f"**Error displaying graph:** {str(e)}")

    mo.md("# Graph Visualization Function")
    return (display_graph_image,)


@app.cell
def _(mo):
    # Cell 13: Display Graph Visualization Header
    mo.md("# **Graph Visualization:**")

    return


@app.cell
def _(display_graph_image, routing_graph):
    # Cell 14: Show Graph Image
    display_graph_image(routing_graph)

    return


@app.cell
def _(mo, routing_graph):
    # Cell 15: Test Routing Path 1
    result2 = routing_graph.invoke({"graph_state": "2"})
    mo.md(f"**Routing Graph Result (input '2'):**\n```python\n{result2}\n```")

    return


@app.cell
def _(mo, routing_graph):
    # Cell 16: Test Routing Path 2
    result3 = routing_graph.invoke({"graph_state": "3"})
    mo.md(f"**Routing Graph Result (input '3'):**\n```python\n{result3}\n```")

    return


@app.cell
def _(mo):
    # Cell 17: Summary
    mo.vstack([
        mo.md("# Summary"),
        mo.md("## This marimo notebook demonstrates:"),
        mo.md("1. **Simple State Management**: Basic state updates through graph execution"),
        mo.md("2. **Conditional Routing**: Dynamic path selection based on input values"),
        mo.md("3. **Graph Visualization**: Visual representation of the graph structure using mermaid diagrams"),
        mo.md("## The key differences from Jupyter:"),
        mo.md("- Uses `mo.md()` for markdown content"),
        mo.md("- Replaces `IPython.display.Image` with base64 encoded HTML images"),
        mo.md("- Maintains all LangGraph functionality while being marimo-compatible")
    ])

    return


@app.cell
def _(mo):
    # Cell 18: Reactive Dependencies Diagram
    mo.vstack([
        mo.md("## Reactive Dependencies Diagram:"),
        mo.md(" "),
        mo.mermaid("""
    graph TD
        C1["Cell 1<br/>📦 Imports & Setup"] --> C2["Cell 2<br/>🔑 Environment"]
        C1 --> C6["Cell 6<br/>📝 State Header"]
        C1 --> C7["Cell 7<br/>🏗️ State Class"]
        C1 --> C8["Cell 8<br/>🔨 Simple Graph"]
        C1 --> C11["Cell 11<br/>🔀 Routing System"]
        C1 --> C12["Cell 12<br/>🖼️ Visualization Function"]
    
        C7 --> C8
        C8 --> C9["Cell 9<br/>▶️ Simple Execution"]
    
        C11 --> C12
        C11 --> C14["Cell 14<br/>📊 Graph Display"]
        C11 --> C15["Cell 15<br/>🎯 Test Path 1"]
        C11 --> C16["Cell 16<br/>🎯 Test Path 2"]
    
        C12 --> C14
    
        %% Independent cells
        C3["Cell 3<br/>📋 Title"]
        C4["Cell 4<br/>📖 Concepts"]
        C5["Cell 5<br/>⚙️ Setup Instructions"]
        C10["Cell 10<br/>🔀 Routing Header"]
        C13["Cell 13<br/>📊 Viz Header"]
        C17["Cell 17<br/>📄 Summary"]
    
        %% Dark theme friendly styling
        classDef primary fill:#1e3a8a,stroke:#3b82f6,stroke-width:3px,color:#ffffff
        classDef secondary fill:#581c87,stroke:#a855f7,stroke-width:2px,color:#ffffff
        classDef independent fill:#166534,stroke:#22c55e,stroke-width:1px,color:#ffffff
        classDef execution fill:#ea580c,stroke:#f97316,stroke-width:2px,color:#ffffff
    
        class C1,C7,C8,C11 primary
        class C2,C12 secondary
        class C3,C4,C5,C6,C10,C13,C17 independent
        class C9,C14,C15,C16 execution
        """),
        mo.md(" "),
        mo.md("### Legend:"),
        mo.md("- **🔵 Primary Cells**: Core functionality (imports, state, graph building)"),
        mo.md("- **🟣 Secondary Cells**: Supporting functions (environment, visualization)"),
        mo.md("- **🟢 Independent Cells**: Standalone markdown content"),
        mo.md("- **🟠 Execution Cells**: Graph execution and display")
    ])
    return


@app.cell
def _(mo):

    mo.vstack([
        mo.md("# **Define Graph Visualization Function**"),
        mo.md(" "),
        mo.md("## **🎯 Key Learning Points:**"),
        mo.md(" "),
        mo.md("1. Same Data Source: Both get PNG bytes from draw_mermaid_png()"),
        mo.md("2. Different Rendering: Jupyter uses kernel magic, Marimo uses web standards"),
        mo.md("3. Reactivity: Jupyter displays once, Marimo creates reactive HTML objects"),
        mo.md("4. Error Handling: Marimo allows custom error messages and troubleshooting"),
        mo.md("5. Styling Control: Marimo gives full HTML/CSS control"),
        mo.md(" "),
        mo.md("## **🚀 Why This Matters:**"),
        mo.md("- **Understanding**: Shows exactly what Jupyter abstracts away"),
        mo.md("- **Debugging**: When images don't show, you know where to look"),
        mo.md("- **Customization**: Full control over styling and behavior"),
        mo.md("- **Portability**: Same pattern works for any binary data visualization"),
        mo.md("- **This conversion pattern can be applied to any Jupyter display object - matplotlib plots, PIL images, SVGs, etc.! 🎨**")
    ])
    return


if __name__ == "__main__":
    app.run()
