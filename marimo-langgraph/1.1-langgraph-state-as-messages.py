import marimo

__generated_with = "0.14.7"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    __generated_with = "0.14.7"
    app = mo.App()

    # Global imports - all defined here for maximum DRY
    import os
    import getpass
    from typing_extensions import TypedDict
    from typing import Annotated
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, AnyMessage
    from langchain_openai import ChatOpenAI
    from langgraph.graph import StateGraph, START, END
    from langgraph.graph.message import add_messages
    from langgraph.graph import MessagesState
    import base64

    mo.md("# **State as Messages - LangGraph Tutorial**")

    return (
        AIMessage,
        Annotated,
        AnyMessage,
        ChatOpenAI,
        END,
        HumanMessage,
        MessagesState,
        StateGraph,
        TypedDict,
        add_messages,
        base64,
        getpass,
        mo,
        os,
    )


@app.cell
def _(getpass, mo, os):
    # CELL 1: Environment Setup
    def setup_environment():
        def _set_env(key: str):
            if key not in os.environ:
                os.environ[key] = getpass.getpass(f"{key}: ")
    
        _set_env("OPENAI_API_KEY")
    
        return mo.vstack([
            mo.md("# **🔑 Environment Setup - API Key Configuration**"),
            mo.md("✅ API key configured successfully")
        ])

    setup_environment()
    return


@app.cell
def _(mo):
    def notebook_introduction():
        # Cell 3: Notebook Introduction
        notebook_introductions = mo.vstack([
            mo.md("# **🚀 State as Messages - LangGraph Tutorial**"),
            mo.md(" "),
            mo.md("## 📋 What You'll Learn:"),
            mo.md("- **Message Types**: Understanding HumanMessage, AIMessage, SystemMessage, ToolMessage"),
            mo.md("- **State Management**: How to keep conversation logs across graph execution"),
            mo.md("- **Reducers**: Using `add_messages` to append rather than override state"),
            mo.md("- **LLM Integration**: Building conversational AI with persistent context"),
            mo.md(" "),
            mo.md("## 🎯 Key Concepts:"),
            mo.md("- Messages capture different roles in conversations"),
            mo.md("- State reducers control how data gets updated"),
            mo.md("- LangGraph provides built-in MessagesState for convenience")
        ])
        return notebook_introductions

    notebook_introduction()
    return


@app.cell
def _(mo):
    # CELL 3: Messages Explanation
    def messages_explanation():
        return mo.vstack([
            mo.md("# **💬 Messages**"),
            mo.md(" "),
            mo.md("## Messages capture different roles within a conversation:"),
            mo.md(" "),
            mo.md("1. **`HumanMessage`** - message from the user"),
            mo.md("2. **`AIMessage`** - message from the chat model"),
            mo.md("3. **`SystemMessage`** - message that instructs the behavior of the chat model"),
            mo.md("4. **`ToolMessage`** - message from a tool call (calling a tool that performs some action)"),
            mo.md(" "),
            mo.md("## Each message can be supplied with:"),
            mo.md("- **`content`** - content of the message"),
            mo.md("- **`name`** - optionally, a message author"),
            mo.md("- **`response_metadata`** - optionally, a dict of metadata")
        ])

    messages_explanation()

    return


@app.cell
def _(AIMessage, HumanMessage, mo):
    # CELL 4: Sample Messages
    def create_sample_messages():
        # Create sample messages
        messages = [AIMessage(content="So, you work in AI engineering?", name="Model")]
        messages.append(HumanMessage(content="Yes, that's right.", name="Lucas"))
        messages.append(AIMessage(content="Great, what would you like to learn about.", name="Model"))
        messages.append(HumanMessage(content="I want to learn about fine tunning local LLMs.", name="Lucas"))

        # Display messages in a formatted way
        message_display = []
        for m in messages:
            msg_type = "🤖 AI" if isinstance(m, AIMessage) else "👤 Human"
            message_display.append(f"**{msg_type} Message ({m.name}):** {m.content}")

        display_content = mo.vstack([
            mo.md("# **📝 Sample Messages**"),
            mo.md(" "),
            mo.md("## Example conversation:"),
            mo.md(" "),
            *[mo.md(msg) for msg in message_display]
        ])
    
        return (messages, display_content)

    messages, sample_display = create_sample_messages()
    sample_display

    return


@app.cell
def _(mo):
    # CELL 5: Messages as State Explanation  
    def messages_as_state_explanation():
        return mo.vstack([
            mo.md("# **🔄 Using Messages as State**"),
            mo.md(" "),
            mo.md("## What do we need to have messages as parts of a graph state?"),
            mo.md(" "),
            mo.md("1. **Storage**: Something that stores the messages (like a list)"),
            mo.md("2. **Appending**: Something that allows us to add more messages as the graph executes"),
            mo.md("3. **Metadata**: Something that can log metadata about objects for debugging"),
            mo.md(" "),
            mo.md("## The Challenge:"),
            mo.md("By default, LangGraph **overrides** the prior state values. But we want to **append** messages to our conversation log!")
        ])

    messages_as_state_explanation()
    return


@app.cell
def _(AnyMessage, TypedDict, mo):
    # CELL 6: Simple Messages State (Without Reducer)
    def simple_messages_state():
        class SimpleMessagesState(TypedDict):
            messages: list[AnyMessage]

        display_content = mo.vstack([
            mo.md("# **📦 Simple Messages State**"),
            mo.md(" "),
            mo.md("## First attempt (without reducer):"),
            mo.md("```python"),
            mo.md("class SimpleMessagesState(TypedDict):"),
            mo.md("    messages: list[AnyMessage]"),
            mo.md("```"),
            mo.md(" "),
            mo.md("⚠️ **Problem**: This will override messages instead of appending them!")
        ])
    
        return (SimpleMessagesState, display_content)

    SimpleMessagesState, simple_state_display = simple_messages_state()
    simple_state_display
    return (SimpleMessagesState,)


@app.cell
def _(END, HumanMessage, SimpleMessagesState, StateGraph, mo):
    # CELL 7: Test Simple State Problem
    def test_simple_state_problem():
        def my_node_override(state):
            new_message = HumanMessage(content="message 1", name="Lucas")
            return {"messages": [new_message]}

        def my_node2_override(state):
            new_message = HumanMessage(content="message 2", name="Lucas")
            return {"messages": [new_message]}

        # Create and test workflow
        workflow_override = StateGraph(SimpleMessagesState)
        workflow_override.add_node("test_node", my_node_override)
        workflow_override.add_node("test_node2", my_node2_override)
        workflow_override.set_entry_point("test_node")
        workflow_override.add_edge("test_node", "test_node2")
        workflow_override.add_edge("test_node2", END)
        graph_override = workflow_override.compile()

        # Test the problem
        result_override = graph_override.invoke({"messages": []})
    
        display_content = mo.vstack([
            mo.md("# **⚠️ The Problem Demonstrated**"),
            mo.md(" "),
            mo.md("## Result with simple state (messages get overridden):"),
            mo.md("```python"),
            mo.md(f"Messages count: {len(result_override['messages'])}"),
            mo.md(f"Final messages: {[m.content for m in result_override['messages']]}"),
            mo.md("```"),
            mo.md(" "),
            mo.md("**Expected**: Both messages should be preserved"),
            mo.md("**Actual**: Only the last message remains! 😞")
        ])
    
        return (graph_override, result_override, display_content)

    graph_override, result_override, problem_display = test_simple_state_problem()
    problem_display

    return


@app.cell
def _(mo):
    # CELL 8: Reducers Explanation
    def reducers_explanation():
        return mo.vstack([
            mo.md("# **🔧 Reducers**"),
            mo.md(" "),
            mo.md("## The Solution: Reducer Functions"),
            mo.md(" "),
            mo.md("In LangGraph, **reducer functions** specify how states get updated."),
            mo.md("To append messages instead of overriding them, we use the `add_messages` reducer."),
            mo.md(" "),
            mo.md("## How it works:"),
            mo.md("- **Default behavior**: Override previous state values"),
            mo.md("- **With `add_messages`**: Append new messages to existing list"),
            mo.md("- **Annotation**: We annotate the `messages` key with metadata")
        ])

    reducers_explanation()

    return


@app.cell
def _(Annotated, AnyMessage, TypedDict, add_messages, mo):
    # CELL 9: Messages State with Reducer
    def messages_state_with_reducer():
        class MessagesStateWithReducer(TypedDict):
            messages: Annotated[list[AnyMessage], add_messages]

        display_content = mo.vstack([
            mo.md("# **✅ Messages State with Reducer**"),
            mo.md(" "),
            mo.md("## Correct implementation:"),
            mo.md("```python"),
            mo.md("from typing import Annotated"),
            mo.md("from langgraph.graph.message import add_messages"),
            mo.md(" "),
            mo.md("class MessagesStateWithReducer(TypedDict):"),
            mo.md("    messages: Annotated[list[AnyMessage], add_messages]"),
            mo.md("```"),
            mo.md(" "),
            mo.md("🎉 **Solution**: The `add_messages` reducer will append instead of override!")
        ])
    
        return (MessagesStateWithReducer, display_content)

    MessagesStateWithReducer, reducer_display = messages_state_with_reducer()
    reducer_display

    return (MessagesStateWithReducer,)


@app.cell
def _(END, HumanMessage, MessagesStateWithReducer, StateGraph, mo):
    # CELL 10: Test Reducer Solution
    def test_reducer_solution():
        def my_node_append(state):
            new_message = HumanMessage(content="message 1", name="Lucas")
            return {"messages": [new_message]}

        def my_node2_append(state):
            new_message = HumanMessage(content="message 2", name="Lucas")
            return {"messages": [new_message]}

        # Create and test workflow
        workflow_append = StateGraph(MessagesStateWithReducer)
        workflow_append.add_node("test_node", my_node_append)
        workflow_append.add_node("test_node2", my_node2_append)
        workflow_append.set_entry_point("test_node")
        workflow_append.add_edge("test_node", "test_node2")
        workflow_append.add_edge("test_node2", END)
        graph_append = workflow_append.compile()

        # Test the solution
        result_append = graph_append.invoke({"messages": []})
    
        display_content = mo.vstack([
            mo.md("# **✅ The Solution Works!**"),
            mo.md(" "),
            mo.md("## Result with reducer (messages get appended):"),
            mo.md("```python"),
            mo.md(f"Messages count: {len(result_append['messages'])}"),
            mo.md(f"Final messages: {[m.content for m in result_append['messages']]}"),
            mo.md("```"),
            mo.md(" "),
            mo.md("**Expected**: Both messages should be preserved"),
            mo.md("**Actual**: Both messages are there! 🎉")
        ])
    
        return (graph_append, result_append, display_content)

    graph_append, result_append, solution_display = test_reducer_solution()
    solution_display

    return (graph_append,)


@app.cell
def _(base64, graph_append, mo):
    # CELL 11: Graph Visualization with Complete Detailed Analysis
    def create_graph_visualization():
        def display_graph_image(graph, title="Graph Visualization"):
            """
            Improved graph visualization function that produces crisp mermaid images
            This replaces the Python display in marimo
            """
            try:
                # Get the mermaid PNG bytes
                png_bytes = graph.get_graph().draw_mermaid_png()
            
                # Convert to base64 for display
                img_base64 = base64.b64encode(png_bytes).decode()
            
                # Create HTML img tag with proper sizing and styling
                html_content = f'''
                <div style="text-align: center; margin: 20px 0;">
                    <img src="data:image/png;base64,{img_base64}" 
                         alt="{title}" 
                         style="max-width: 600px; height: auto; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                </div>
                '''
            
                return mo.Html(html_content)
            except Exception as e:
                return mo.md(f"**Error displaying graph:** {str(e)}")
    
        # Create the complete detailed analysis with consistent formatting
        detailed_analysis = mo.vstack([
            mo.md("# **📊 Reducer Solution Graph Structure**"),
            mo.md("This graph demonstrates the **reducer solution** that properly appends messages instead of overriding them:"),
            display_graph_image(graph_append, "Reducer Graph Structure"),
        
            mo.md("🔍 **Detailed Component Analysis**"),
            mo.md("🟢 **START Node**"),
            mo.md("* **Purpose**: Entry point for graph execution"),
            mo.md("* **Initial State**: `{\"messages\": []}` (empty message list)"),
            mo.md("* **Routing**: Automatically flows to `test_node`"),
            mo.md("* **Key Feature**: Sets up the initial state structure"),
        
            mo.md("🔵 **test_node (Node 1)**"),
            mo.md("* **Function**: `my_node_append(state)`"),
            mo.md("* **Input**: `{\"messages\": []}`"),
            mo.md("* **Process**:"),
            mo.md("  1. Creates `HumanMessage(content=\"message 1\", name=\"Lucas\")`"),
            mo.md("  2. Returns `{\"messages\": [new_message]}`"),
            mo.md("* **State After**: `{\"messages\": [HumanMessage(\"message 1\")]}`"),
            mo.md("* **Reducer Action**: `add_messages` appends to existing list"),
            mo.md("* **Next**: Flows to `test_node2`"),
        
            mo.md("🔵 **test_node2 (Node 2)**"),
            mo.md("* **Function**: `my_node2_append(state)`"),
            mo.md("* **Input**: `{\"messages\": [HumanMessage(\"message 1\")]}`"),
            mo.md("* **Process**:"),
            mo.md("  1. Creates `HumanMessage(content=\"message 2\", name=\"Lucas\")`"),
            mo.md("  2. Returns `{\"messages\": [new_message]}`"),
            mo.md("* **State After**: `{\"messages\": [HumanMessage(\"message 1\"), HumanMessage(\"message 2\")]}`"),
            mo.md("* **Reducer Action**: `add_messages` appends second message"),
            mo.md("* **Next**: Flows to `END`"),
        
            mo.md("🔴 **END Node**"),
            mo.md("* **Purpose**: Terminates graph execution"),
            mo.md("* **Final State**: `{\"messages\": [message1, message2]}`"),
            mo.md("* **Result**: **Both messages preserved!** ✅"),
            mo.md("* **Success**: Demonstrates proper reducer functionality"),
        
            mo.md("🧠 **State Management Deep Dive**"),
            mo.md("**MessagesStateWithReducer Definition:**"),
            mo.md("```python"),
            mo.md("class MessagesStateWithReducer(TypedDict):"),
            mo.md("    messages: Annotated[list[AnyMessage], add_messages]"),
            mo.md("```"),
            mo.md("**Reducer Behavior Analysis:**"),
            mo.md("* **Without Reducer**: `new_state = {\"messages\": [new_message]}` → **Overrides**"),
            mo.md("* **With add_messages**: `existing_messages + [new_message]` → **Appends**"),
            mo.md("**Execution Flow Trace:**"),
            mo.md("```python"),
            mo.md("# Step 1: Initial invocation"),
            mo.md("graph_append.invoke({\"messages\": []})"),
            mo.md(""),
            mo.md("# Step 2: START → test_node"),
            mo.md("state = {\"messages\": []}"),
            mo.md("node1_result = {\"messages\": [HumanMessage(\"message 1\")]}"),
            mo.md("# add_messages: [] + [message1] = [message1]"),
            mo.md(""),
            mo.md("# Step 3: test_node → test_node2"),
            mo.md("state = {\"messages\": [HumanMessage(\"message 1\")]}"),
            mo.md("node2_result = {\"messages\": [HumanMessage(\"message 2\")]}"),
            mo.md("# add_messages: [message1] + [message2] = [message1, message2]"),
            mo.md(""),
            mo.md("# Step 4: test_node2 → END"),
            mo.md("final_state = {\"messages\": [message1, message2]}"),
            mo.md("```"),
        
            mo.md("🎯 **Key Success Factors**"),
            mo.md("1. **Proper State Annotation**"),
            mo.md("* `Annotated[list[AnyMessage], add_messages]` enables appending"),
            mo.md("* Without annotation: messages get overridden"),
            mo.md("* Reducer function controls merge behavior"),
            mo.md("2. **Linear Execution Pattern**"),
            mo.md("* **Sequential processing**: Each node builds on previous state"),
            mo.md("* **Deterministic flow**: START → Node1 → Node2 → END"),
            mo.md("* **State accumulation**: Each step adds to the conversation"),
            mo.md("3. **Message Preservation**"),
            mo.md("* **Conversation history**: All messages maintained"),
            mo.md("* **Context awareness**: Each node sees full history"),
            mo.md("* **No data loss**: Critical for conversational AI"),
        
            mo.md("🚀 **Practical Applications**"),
            mo.md("This pattern enables:"),
            mo.md("* **💬 Multi-turn conversations**: Each response builds on previous context"),
            mo.md("* **🤖 AI assistants**: Maintain conversation memory"),
            mo.md("* **📞 Customer service bots**: Track entire interaction history"),
            mo.md("* **🎓 Educational tutors**: Remember student questions and progress"),
            mo.md("* **🔧 Debugging tools**: Log all state transitions"),
        
            mo.md("⚠️ **What This Fixes**"),
            mo.md("**Before (Simple State)**:"),
            mo.md("* Messages count: 1"),
            mo.md("* Final messages: ['message 2']"),
            mo.md("* Result: ❌ Lost 'message 1'"),
            mo.md("**After (Reducer State)**:"),
            mo.md("* Messages count: 2"),
            mo.md("* Final messages: ['message 1', 'message 2']"),
            mo.md("* Result: ✅ Both messages preserved!")
        ])
    
        return (display_graph_image, detailed_analysis)

    # Execute and display everything
    display_graph_image, detailed_analysis = create_graph_visualization()
    detailed_analysis
    return (display_graph_image,)


@app.cell
def _(mo):
    # CELL 12: Built-in MessagesState
    def builtin_messages_state():
        return mo.vstack([
            mo.md("# **🎁 LangGraph Built-in MessagesState**"),
            mo.md(" "),
            mo.md("## Good news! LangGraph provides a built-in MessagesState:"),
            mo.md("```python"),
            mo.md("from langgraph.graph import MessagesState"),
            mo.md("```"),
            mo.md(" "),
            mo.md("## This is equivalent to our custom implementation:"),
            mo.md("```python"),
            mo.md("class MessagesState(TypedDict):"),
            mo.md("    messages: Annotated[list[AnyMessage], add_messages]"),
            mo.md("```"),
            mo.md(" "),
            mo.md("💡 **Use the built-in version** - it's tested and optimized!")
        ])

    builtin_messages_state()

    return


@app.cell
def _(ChatOpenAI, END, MessagesState, StateGraph, mo):
    # CELL 13: LLM Integration Example
    def llm_integration_example():
        # Initialize the LLM
        llm = ChatOpenAI()

        def chat_node(state):
            messages = state["messages"]
            response = llm.invoke(messages)
            return {"messages": [response]}

        # Create workflow
        workflow_chat = StateGraph(MessagesState)
        workflow_chat.add_node("chat", chat_node)
        workflow_chat.set_entry_point("chat")
        workflow_chat.add_edge("chat", END)
        app_chat = workflow_chat.compile()

        display_content = mo.vstack([
            mo.md("# **🤖 LLM Integration Example**"),
            mo.md(" "),
            mo.md("## Simple Chat Bot:"),
            mo.md("```python"),
            mo.md("def chat_node(state):"),
            mo.md("    messages = state['messages']"),
            mo.md("    response = llm.invoke(messages)"),
            mo.md("    return {'messages': [response]}"),
            mo.md("```"),
            mo.md(" "),
            mo.md("The `add_messages` reducer automatically appends the LLM response!")
        ])
    
        return (app_chat, display_content)

    app_chat, llm_display = llm_integration_example()
    llm_display

    return (app_chat,)


@app.cell
def _(HumanMessage, app_chat, mo):
    # CELL 14: Test LLM Chat
    def test_llm_chat():
        try:
            result_chat = app_chat.invoke({
                "messages": [HumanMessage("Tell me a joke about pancakes.")]
            })
        
            conversation = []
            for msg in result_chat["messages"]:
                msg_type = "🤖 AI" if hasattr(msg, 'content') and not isinstance(msg, HumanMessage) else "👤 Human"
                conversation.append(f"**{msg_type}:** {msg.content}")
        
            display_content = mo.vstack([
                mo.md("# **🎭 LLM Chat Test**"),
                mo.md(" "),
                mo.md("## Complete Conversation:"),
                mo.md(" "),
                *[mo.md(msg) for msg in conversation],
                mo.md(" "),
                mo.md(f"**Total messages in conversation:** {len(result_chat['messages'])}")
            ])
        
        except Exception as e:
            display_content = mo.vstack([
                mo.md("# **🎭 LLM Chat Test**"),
                mo.md(" "),
                mo.md(f"**Note:** LLM test requires valid OpenAI API key. Error: {str(e)}")
            ])
    
        return display_content

    test_llm_chat()

    return


@app.cell
def _(app_chat, display_graph_image, mo):
    # CELL 15: Show Chat Graph Visualization with Detailed Explanation
    def show_chat_graph():
        return mo.vstack([
            mo.md("# **📊 Chat Graph Visualization**"),
            mo.md("This graph represents our **complete conversational AI system** using LangGraph with built-in `MessagesState`:"),
            display_graph_image(app_chat, "Chat Bot Graph Structure"),
        
            mo.md("🔍 **Graph Components Explained**"),
            mo.md("🟢 **START Node**"),
            mo.md("* **Purpose**: Entry point for the conversation"),
            mo.md("* **Input**: Initial state with user's message"),
            mo.md("* **Flow**: Automatically routes to the `chat` node"),
        
            mo.md("🔵 **chat Node**"),
            mo.md("* **Function**: `chat_node(state)`"),
            mo.md("* **Process**:"),
            mo.md("  1. Extracts `messages` from current state"),
            mo.md("  2. Sends messages to OpenAI LLM via `llm.invoke()`"),
            mo.md("  3. Receives AI response"),
            mo.md("  4. Returns `{\"messages\": [response]}`"),
            mo.md("* **Key Feature**: Uses `add_messages` reducer to append (not override!)"),
        
            mo.md("🔴 **END Node**"),
            mo.md("* **Purpose**: Terminates the graph execution"),
            mo.md("* **Output**: Final state with complete conversation history"),
            mo.md("* **Result**: Both user message AND AI response preserved"),
        
            mo.md("💡 **Data Flow Example**"),
            mo.md("```python"),
            mo.md("# Input State"),
            mo.md("initial_state = {"),
            mo.md("    'messages': [HumanMessage('Tell me a joke about pancakes.')]"),
            mo.md("}"),
            mo.md(""),
            mo.md("# After chat_node processing"),
            mo.md("final_state = {"),
            mo.md("    'messages': ["),
            mo.md("        HumanMessage('Tell me a joke about pancakes.'),"),
            mo.md("        AIMessage('Why did the pancake go to therapy?...')"),
            mo.md("    ]"),
            mo.md("}"),
            mo.md("```"),
        
            mo.md("🎯 **Key LangGraph Concepts Demonstrated**"),
            mo.md("1. **Built-in MessagesState**"),
            mo.md("* Uses `MessagesState` (equivalent to our custom reducer implementation)"),
            mo.md("* Automatically handles message appending with `add_messages`"),
            mo.md("* No manual state management required"),
            mo.md("2. **Linear Execution Flow**"),
            mo.md("* **START** → **chat** → **END** (simple sequential processing)"),
            mo.md("* Perfect for single-turn conversations"),
            mo.md("* Can be extended with conditional routing for multi-turn dialogs"),
            mo.md("3. **State Persistence**"),
            mo.md("* Conversation history maintained throughout execution"),
            mo.md("* Each node can access full message context"),
            mo.md("* Enables context-aware AI responses"),
        
            mo.md("🚀 **Production Extensions**"),
            mo.md("This simple graph can be extended with:"),
            mo.md("* **🔄 Conditional routing**: Different responses based on user intent"),
            mo.md("* **🛠️ Tool integration**: Function calling capabilities"),
            mo.md("* **🧠 Memory management**: Conversation summarization for long chats"),
            mo.md("* **🎭 Persona switching**: Multiple AI personalities"),
            mo.md("* **📊 Analytics**: Conversation tracking and insights"),
        
            mo.md("⚡ **Performance Notes**"),
            mo.md("* **Stateless execution**: Each invocation is independent"),
            mo.md("* **Reducer efficiency**: `add_messages` is optimized for message handling"),
            mo.md("* **LLM caching**: OpenAI responses can be cached for identical inputs"),
            mo.md("* **Async support**: Can be extended for concurrent processing")
        ])

    show_chat_graph()
    return


@app.cell
def _(mo):
    # CELL 16: Key Takeaways
    def key_takeaways():
        return mo.vstack([
            mo.md("# **🎯 Key Takeaways**"),
            mo.md(" "),
            mo.md("## What we learned:"),
            mo.md(" "),
            mo.md("1. **Message Types**: Different roles in conversations (Human, AI, System, Tool)"),
            mo.md("2. **State Management**: Using TypedDict to define graph state structure"),
            mo.md("3. **Reducer Functions**: `add_messages` appends instead of overriding"),
            mo.md("4. **Built-in Convenience**: LangGraph provides `MessagesState` out of the box"),
            mo.md("5. **LLM Integration**: Easy to build conversational AI with persistent context"),
            mo.md(" "),
            mo.md("## The Pattern:"),
            mo.md("```python"),
            mo.md("# 1. Define state with reducer"),
            mo.md("class MessagesState(TypedDict):"),
            mo.md("    messages: Annotated[list[AnyMessage], add_messages]"),
            mo.md(" "),
            mo.md("# 2. Create nodes that return message lists"),
            mo.md("def chat_node(state):"),
            mo.md("    response = llm.invoke(state['messages'])"),
            mo.md("    return {'messages': [response]}"),
            mo.md(" "),
            mo.md("# 3. Build and compile graph"),
            mo.md("workflow = StateGraph(MessagesState)"),
            mo.md("workflow.add_node('chat', chat_node)"),
            mo.md("app = workflow.compile()"),
            mo.md("```")
        ])

    key_takeaways()


    return


@app.cell
def _(mo):
    # CELL 17: Summary and Next Steps
    def summary_and_next_steps():
        return mo.vstack([
            mo.md("# **📋 Summary & Next Steps**"),
            mo.md(" "),
            mo.md("## 🎉 Congratulations!"),
            mo.md("You now understand how to:"),
            mo.md("- Use messages as state in LangGraph"),
            mo.md("- Control state updates with reducer functions"),
            mo.md("- Build conversational AI systems"),
            mo.md("- Maintain conversation context across graph execution"),
            mo.md(" "),
            mo.md("## 🚀 What's Next?"),
            mo.md("- **Multi-turn conversations**: Handle back-and-forth dialogue"),
            mo.md("- **Tool integration**: Add function calling capabilities"),
            mo.md("- **Conditional routing**: Different responses based on context"),
            mo.md("- **Memory management**: Handle long conversations efficiently"),
            mo.md(" "),
            mo.md("## 💡 Pro Tips:"),
            mo.md("- Always use `MessagesState` for message-based graphs"),
            mo.md("- Test your reducers to ensure proper state updates"),
            mo.md("- Consider message limits for long conversations"),
            mo.md("- Use proper error handling for LLM calls")
        ])

    summary_and_next_steps()

    return


@app.cell
def _(mo):
    # CELL 18: Reactive Dependencies Diagram
    def reactive_dependencies_diagram():
        return mo.vstack([
            mo.md("# **🔄 Reactive Dependencies Diagram**"),
            mo.md(" "),
            mo.md("## Visual representation of how cells depend on each other:"),
            mo.md(" "),
            mo.mermaid("""
    graph TD
        C1["Cell 1<br/>🔑 Environment Setup"] --> C2["Cell 2<br/>📋 Introduction"]
        C1 --> C3["Cell 3<br/>💬 Messages Explanation"]
        C1 --> C4["Cell 4<br/>📝 Sample Messages"]
        C1 --> C6["Cell 6<br/>📦 Simple State"]
        C1 --> C7["Cell 7<br/>⚠️ State Problem Demo"]
        C1 --> C9["Cell 9<br/>✅ Reducer State"]
        C1 --> C10["Cell 10<br/>🔧 Reducer Test"]
        C1 --> C11["Cell 11<br/>📊 Graph Visualization"]
        C1 --> C13["Cell 13<br/>🤖 LLM Integration"]

        C4 --> C5["Cell 5<br/>🔄 State Explanation"]
        C6 --> C7
        C7 --> C8["Cell 8<br/>🔧 Reducers Explanation"]
        C8 --> C9
        C9 --> C10
        C10 --> C11
        C11 --> C15["Cell 15<br/>📊 Chat Graph Viz"]
        C13 --> C14["Cell 14<br/>🎭 LLM Chat Test"]
        C13 --> C15

        %% Independent cells
        C12["Cell 12<br/>🎁 Built-in MessagesState"]
        C16["Cell 16<br/>🎯 Key Takeaways"]
        C17["Cell 17<br/>📋 Summary & Next Steps"]

        %% Dark theme friendly styling
        classDef primary fill:#1e3a8a,stroke:#3b82f6,stroke-width:3px,color:#ffffff
        classDef secondary fill:#581c87,stroke:#a855f7,stroke-width:2px,color:#ffffff
        classDef independent fill:#166534,stroke:#22c55e,stroke-width:1px,color:#ffffff
        classDef execution fill:#ea580c,stroke:#f97316,stroke-width:2px,color:#ffffff
        classDef demo fill:#dc2626,stroke:#f87171,stroke-width:2px,color:#ffffff

        class C1 primary
        class C6,C7,C9,C10,C11,C13 secondary
        class C2,C3,C5,C8,C12,C16,C17 independent
        class C4,C14,C15 execution
        class C7 demo
            """),
            mo.md(" "),
            mo.md("### 📊 Legend:"),
            mo.md("- **🔵 Primary**: Core foundation (environment setup)"),
            mo.md("- **🟣 Secondary**: Main functionality (states, graphs, LLM)"),
            mo.md("- **🟢 Independent**: Standalone content (explanations, summaries)"),
            mo.md("- **🟠 Execution**: Interactive demonstrations"),
            mo.md("- **🔴 Demo**: Problem/solution demonstrations"),
            mo.md(" "),
            mo.md("### 🎯 Key Insights:"),
            mo.md("- **Cell 1** is the foundation - all functional cells depend on it"),
            mo.md("- **Linear progression** from simple state → reducer solution → LLM integration"),
            mo.md("- **Independent cells** can be reordered without breaking dependencies"),
            mo.md("- **Clean separation** between explanation and demonstration cells")
        ])

    reactive_dependencies_diagram()
    return


if __name__ == "__main__":
    app.run()
