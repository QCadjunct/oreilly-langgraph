import marimo

__generated_with = "0.14.7"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    import quarto
    __version__ = "0.1.0"
    __generated_with = "0.14.7"

    mo.md("✅ All imports installed successfully!")
    return (mo,)


@app.cell
def _(mo):
    mo.md(
        """
    # 🚀 Practical Introduction to LangGraph

    This notebook provides a hands-on introduction to LangGraph fundamentals:
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


@app.cell
def _(mo):
    def load_required_packages():
        try:
            import langgraph
            import openai
            result = mo.md(
                f"""
                ✅ **All packages loaded successfully!**
                - **LangGraph**: {langgraph}
                - **OpenAI**: {openai.__version__}
                """
            )
            return result, langgraph, openai
        except ImportError as e:
            return mo.md(
                f"""
                ❌ **Missing package**: {e}
                Please run `uv sync` from the project root to install all dependencies.
                """
            )

    # Different variable names to avoid conflicts
    package_status, lg, oai = load_required_packages()
    package_status
    return


@app.cell
def _(display, mo):
    import os
    from dotenv import load_dotenv
    import getpass

    # Load environment variables from .env file
    load_dotenv()

    def setup_api_key(var_name: str, service_name: str = None):
        """Setup API key from .env file or prompt user"""
        service = service_name or var_name.replace("_API_KEY", "")
        warning_md = None

        if not os.environ.get(var_name):
            # Use mo.md instead of print for warning
            warning_md = mo.md(f"⚠️ **Warning:** {var_name} not found in .env file")

            # Display the warning
            display(warning_md)

            api_key = getpass.getpass(f"Enter your {service} API key: ")
            os.environ[var_name] = api_key
            status = f"✅ {service} API key configured"
        else:
            status = f"✅ {service} API key loaded from .env file"

        # Return a tuple with the Markdown output and any other useful objects
        return mo.md(f"**API Key Status:** {status}"), os, getpass, load_dotenv
    return (setup_api_key,)


@app.cell
def _(setup_api_key):
    # Call the function with tuple unpacking
    api_status, os_module, getpass_module, load_dotenv_func = setup_api_key("OPENAI_API_KEY", "OpenAI")

    # Display the markdown output
    api_status
    return


@app.cell
def _(mo):
    mo.md(
        """
    ## 📊 Understanding States

    **States** are typed data structures that get updated as we execute our graph.
    Think of them as the "memory" of your workflow that carries information between nodes.

    ## 🔧 Understanding Nodes

    **Nodes** are functions that perform computations and update state data.
    Each node receives the current state and returns an updated version.

    ## 🔗 Understanding Edges

    **Edges** connect nodes together in your workflow:
    - **Direct edges**: Simple A → B connections
    - **Conditional edges**: A → B or A → C based on logic

    ## 🌐 Understanding Graphs

    **Graphs** combine everything into a complete workflow.
    They follow a [Directed Acyclic Graph (DAG)](https://en.wikipedia.org/wiki/Directed_acyclic_graph) pattern.

    ## 🎯 Building Your First Graph

    Let's create a simple graph with one node that processes state data.
    """
    )
    return


@app.cell
def _(mo):
    from typing_extensions import TypedDict

    def define_state_schema():
        """Define the state schema for the graph"""
        class State(TypedDict):    
            state_before_node1: str
            state_after_node1: str
    
        is_ready = True
    
        return State, TypedDict, mo.md(
            """
            📋 **State schema defined:** \n
            - `state_before_node1`: Input data\n 
            - `state_after_node1`: Output data
        
            ✅ **Ready for execution!**
            """
        ), is_ready

    # Define the state
    State, TypedDict, state_description, is_ready = define_state_schema()

    # Display state description
    state_description
    return State, TypedDict


@app.cell
def _(mo):
    mo.md(
        """
    ### 🔨 Creating a Processing Node

    Now we'll define a node function that processes our state data.
    """
    )
    return


@app.cell
def _(display, mo):
    def create_node(node_number: int):
        """
        Create a node processing function with a specific node number
    
        Args:
        - node_number: The number of the node to process
    
        Returns:
        - A function that processes the state for the given node
        """
        def node_func(state):
            """Process state data in node number"""
        
            # Get the correct input state key
            input_key = f"state_before_node{node_number}"
            output_key = f"state_after_node{node_number}"
        
            # Process the state
            state[output_key] = f"✅ Successfully processed by node{node_number}"
        
            # Create the display output
            display_output = mo.vstack([
                mo.md(f"🔄 Processing in node {node_number}..."),
                mo.md(f"   Input: {state[input_key]}"),
                mo.md(f"   Output: {state[output_key]}")
            ])
        
            display(display_output)
        
            return state
    
        return node_func
    return (create_node,)


@app.cell
def _(State, create_node, mo):
    from typing import NamedTuple
    from langgraph.graph import StateGraph, START, END

    class GraphInfo(NamedTuple):
        graph: object
        description: object

    def create_and_describe_graph():
        """
        Create and compile the LangGraph
    
        Returns:
        - Compiled graph
        - Markdown description of graph structure
        """
        # Create node functions for each node
        node1 = create_node(1)

        # Create the graph builder
        builder = StateGraph(State)

        # Add our processing node
        builder.add_node("node1", node1)

        # Connect START → node1 → END
        builder.add_edge(START, "node1")
        builder.add_edge("node1", END)

        # Compile the graph
        graph = builder.compile()

        # Create markdown description
        graph_description = mo.md("""
        🎯 **Graph compiled successfully!**
    
        Structure: 
        ```
        START → node1 → END
        ```
        """)

        # Return both the graph and its description
        return GraphInfo(graph=graph, description=graph_description)

    # Call the function and unpack the results
    graph_info = create_and_describe_graph()

    # Display the graph description
    graph_info.description

    return END, START, StateGraph


@app.cell
def _(mo):
    mo.md(
        r"""
    "******* remove ********"

    from typing import Literal
    import random

    def node1(state):
        \"""Process state data in node 1\"""
        print("🔄 Processing in node 1...")
        state["state_after_node1"] = "✅ Successfully processed by node1"
        print(f"   Input: {state['state_before_node1']}")
        print(f"   Output: {state['state_after_node1']}")
        return state
    """
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
    ### 🏗️ Building the Graph

    Now we'll assemble everything into a complete graph with proper edges.
    """
    )
    return


@app.cell
def _(State, mo, node):
    from langgraph.graph import StateGraph, START, END

    # Create the graph builder
    builder = StateGraph(State)

    # Add our processing node
    builder.add_node("node1", node)

    # Connect START → node1 → END
    builder.add_edge(START, "node1")
    builder.add_edge("node1", END)

    # Compile the graph
    graph = builder.compile()

    mo.vstack(
        [
            mo.md("🎯 Graph compiled successfully!"),
            mo.md("   Structure: START → node1 → END"),
        ]
    )
    return END, START, StateGraph, graph


@app.cell
def _(mo):
    mo.md(
        """
    ### 📊 Graph Visualization

    Let's visualize our graph structure:
    """
    )
    return


@app.cell
def _(display, graph, mo):
    # Visualization with better error handling
    try:
        # First attempt: Try to get SVG which might be more compatible
        try:
            graph_svg = graph.get_graph().draw_mermaid_svg()
            mo.html(graph_svg)
        except AttributeError:
            # If SVG not available, try PNG
            graph_png = graph.get_graph().draw_mermaid_png()
            mo.image(src=graph_png)
    except Exception as e:
        error_message = mo.md(f"**Graph visualization not available**: {e}")
        display(error_message)

        # Provide a fallback ASCII visualization
        ascii_viz = mo.md("""
        ## Graph Structure
        ```
        START
          ↓
        node1
          ↓
         END
        ```
        """)
        display(ascii_viz)

        # Try alternative visualization if available
        try:
            # Get the Mermaid code directly if possible
            mermaid_code = graph.get_graph().get_mermaid()
            mermaid_viz = mo.md(f"""
            ## Mermaid Diagram Code
            ```mermaid
            {mermaid_code}
            ```
            """)
            display(mermaid_viz)
        except Exception:
            pass
    return


@app.cell
def _(mo):
    mo.md(
        """
    ### 🚀 Running the Graph

    Now let's execute our graph with some sample data:
    """
    )
    return


@app.cell
def _(graph, mo):
    # Execute the graph
    input_data = {"state_before_node1": "🎯 Processing LangGraph tutorial data!"}

    print("🏃 Executing graph...")
    result1 = graph.invoke(input_data)

    mo.md(f"""
    **Execution Result:**

    ```json
    {result1}
    ```
    """)
    return


@app.cell
def _(mo):
    mo.md(
        """
    ## 🔀 Advanced: Conditional Routing

    Now let's build a more sophisticated graph with **conditional routing**.
    This allows your graph to make decisions and follow different paths.

    ![Routing Diagram](./2025-02-10-12-16-57.png)
    """
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
    ### 🎯 Routing Logic

    We'll create a graph that routes to different nodes based on user input:
    - Input "2" → goes to node2
    - Any other input → goes to node3
    """
    )
    return


@app.cell
def _(Literal):
    def node1_routing(state):
        """Entry point for routing logic"""
        print("🚪 Entering routing node...")
        print(f"   Input: {state.get('graph_state', 'None')}")
        return state

    def node2(state):
        """Processing path A"""
        print("🎯 Processing in node 2")
        state["graph_state"] = "✅ Completed path A (node 2)" 
        return state

    def node3(state):
        """Processing path B"""
        print("🎯 Processing in node 3")
        state["graph_state"] = "✅ Completed path B (node 3)"
        return state

    def decision_node(state) -> Literal["node2", "node3"]:
        """Routing decision logic"""
        user_input = state["graph_state"]
        print(f"🤔 Making routing decision for input: '{user_input}'")

        if user_input == "2":
            print("   → Routing to node2")
            return "node2"
        else:
            print("   → Routing to node3")
            return "node3"

    return decision_node, node1_routing, node2, node3


@app.cell
def _(mo):
    mo.md(
        """
    ### 🏗️ Building the Routing Graph

    Now we'll create a graph with conditional edges:
    """
    )
    return


@app.cell
def _(
    END,
    START,
    StateGraph,
    TypedDict,
    decision_node,
    node1_routing,
    node2,
    node3,
):
    class RoutingState(TypedDict):
        graph_state: str

    # Build the routing graph
    routing_builder = StateGraph(RoutingState)

    # Add all nodes
    routing_builder.add_node("node1", node1_routing)
    routing_builder.add_node("node2", node2)
    routing_builder.add_node("node3", node3)

    # Create the flow: START → node1 → [node2 OR node3] → END
    routing_builder.add_edge(START, "node1")
    routing_builder.add_conditional_edges("node1", decision_node)
    routing_builder.add_edge("node2", END)
    routing_builder.add_edge("node3", END)

    routing_graph = routing_builder.compile()

    print("🎯 Routing graph compiled successfully!")
    print("   Structure: START → node1 → [node2 OR node3] → END")
    return (routing_graph,)


@app.cell
def _(mo):
    mo.md("""### 📊 Routing Graph Visualization""")
    return


@app.cell
def _(mo, routing_graph):
    try:
        routing_graph_png = routing_graph.get_graph().draw_mermaid_png()
        mo.image(src=routing_graph_png)
    except Exception as e:
        mo.md(f"**Routing graph visualization not available**: {e}")
        mo.md(
            """
            ```
            START → node1 → decision
                          ├─ "2" → node2 → END
                          └─ else → node3 → END
            ```
            """
        )
    return


@app.cell
def _(mo):
    mo.md(
        """
    ### 🧪 Testing Routing Paths

    Let's test both routing paths:
    """
    )
    return


@app.cell
def _(mo, routing_graph):
    # Test path to node2
    print("🧪 Testing route to node2 (input='2'):")
    result2 = routing_graph.invoke({"graph_state": "2"})

    mo.md(f"""
    **Route to Node2 (input="2"):**

    ```json
    {result2}
    ```
    """)
    return


@app.cell
def _(mo, routing_graph):
    # Test path to node3
    print("🧪 Testing route to node3 (input='other'):")
    result3 = routing_graph.invoke({"graph_state": "anything_else"})

    mo.md(f"""
    **Route to Node3 (input="anything_else"):**

    ```json
    {result3}
    ```
    """)
    return


@app.cell
def _(mo):
    mo.md(
        """
    ## 🎉 Congratulations!

    You've successfully learned the fundamentals of LangGraph:

    ✅ **States** - Typed data structures for workflow memory  
    ✅ **Nodes** - Processing functions that transform state  
    ✅ **Edges** - Connections between nodes (direct and conditional)  
    ✅ **Graphs** - Complete workflows that orchestrate everything  

    ### 🚀 Next Steps

    - Explore more complex state structures
    - Add error handling and validation
    - Integrate with LLMs for AI-powered workflows
    - Build multi-agent systems

    **Happy graphing!** 🎯
    """
    )
    return


if __name__ == "__main__":
    app.run()
