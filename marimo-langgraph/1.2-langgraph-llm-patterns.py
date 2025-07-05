import marimo

__generated_with = "0.14.7"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    __generated_with = "0.14.7"
    app = mo.App()

    # Global imports - all defined here for maximum DRY
    import getpass
    import os
    import base64
    from langchain_ollama import OllamaLLM, ChatOllama   
    from typing import Annotated, TypedDict
    from typing_extensions import TypedDict
    from langgraph.graph.message import add_messages, AnyMessage
    from langgraph.graph import StateGraph, START, END
    from langchain_ollama import ChatOllama
    from langchain_openai import ChatOpenAI
    from pydantic import BaseModel, Field
    from IPython.display import display, Image, Markdown

    mo.md("# **State as Messages - LangGraph Tutorial**")

    return (
        Annotated,
        AnyMessage,
        BaseModel,
        ChatOllama,
        ChatOpenAI,
        END,
        Field,
        START,
        StateGraph,
        TypedDict,
        add_messages,
        base64,
        getpass,
        mo,
        os,
    )


@app.cell
def _(mo):
    # Introduction - What is a reducer function?
    def reducer_introduction():
        return mo.vstack([
            mo.md("# **Quick Detour - What is a reducer function?**"),
            mo.md("## **A reducer function in LangGraph controls how state gets updated when nodes return new data.**")
        ])

    reducer_introduction()
    return


@app.cell
def _(Annotated, AnyMessage, TypedDict, add_messages, mo):
    # Define MessagesState with reducer
    def define_messages_state():
        class MessagesState(TypedDict):
            messages: Annotated[list[AnyMessage], add_messages]  # we add messages when they go through nodes instead of overriding them.
    
        display_content = mo.vstack([
            mo.md("# **📦 Messages State Definition**"),
            mo.md("```python"),
            mo.md("class MessagesState(TypedDict):"),
            mo.md("    messages: Annotated[list[AnyMessage], add_messages]"),
            mo.md("```"),
            mo.md("## **The `add_messages` reducer appends new messages instead of overriding them.**")
        ])
    
        return (MessagesState, display_content)

    MessagesState, messages_state_display = define_messages_state()
    messages_state_display

    return


@app.cell
def _(mo):
    # Simple node example
    def simple_node_example():
        def node1(state):
            return {"messages": [2]}  # this will be added to the list instead of overriding the list!
    
        display_content = mo.vstack([
            mo.md("# **🔧 Simple Node Example**"),
            mo.md(" "),
            mo.md("## **def node1(state):**"),
            mo.md("### **return {'messages': [2]}  # Added to list, not overridden**"),
            mo.md(" "),
            mo.md("## **This demonstrates how the reducer function works in practice.**")
        ])
    
        return (node1, display_content)

    node1, node_display = simple_node_example()
    node_display
    return


@app.cell
def _(mo):
    # Chaining Pattern for Quiz Generation
    def chaining_pattern_introduction():
        return mo.vstack([
            mo.md("# **🔗 Chaining Pattern for Quiz Generation**"),
            mo.md("## **Inspired by [Anthropic's article on building effective agents](https://www.anthropic.com/research/building-effective-agents).**"),
            mo.md("### **This pattern chains multiple LLM calls together to create a comprehensive quiz generation system.**")
        ])

    chaining_pattern_introduction()

    return


@app.cell
def _(getpass, mo, os):
    # Environment setup for LLM
    def setup_llm_environment():
        def _set_env(key: str):
            if key not in os.environ:
                os.environ[key] = getpass.getpass(f"{key}:")
    
        _set_env("OPENAI_API_KEY")
    
        display_content = mo.vstack([
            mo.md("# **🔑 Environment Setup**"),
            mo.md("## **✅ API key configured for LLM access**")
        ])
    
        return display_content

    setup_llm_environment()
    return


@app.cell
def _(ChatOllama, mo):
    # Initialize LLM models
    def initialize_llm_models():
        llm = ChatOllama(model="llama3.2")
        llm_structured = ChatOllama(model="llama3.2", format="json")
    
        display_content = mo.vstack([
            mo.md("# **🤖 LLM Models Initialized**"),
            mo.md("## Standard LLM: ChatOllama (llama3.2)"),
            mo.md("## Structured LLM: ChatOllama with JSON format")
        ])
    
        return (llm, llm_structured, display_content)

    llm, llm_structured, llm_display = initialize_llm_models()
    llm_display
    return (llm,)


@app.cell
def _(BaseModel, Field, mo):
    # Define review output structure
    def define_review_structure():
        class ReviewOutput(BaseModel):
            quiz_score: str = Field(description="'APPROVED' or 'TO-REVIEW'")
    
        display_content = mo.vstack([
            mo.md("# **📋 Review Output Structure**"),
            mo.md(" "),
            mo.md("## **class ReviewOutput(BaseModel):**"),
            mo.md("###    quiz_score: str = Field(description=\"'APPROVED' or 'TO-REVIEW'\")"),
            mo.md(" "),
            mo.md("### **This structure ensures consistent review responses.**")
        ])
    
        return (ReviewOutput, display_content)

    ReviewOutput, review_structure_display = define_review_structure()
    review_structure_display

    return (ReviewOutput,)


@app.cell
def _(ReviewOutput, llm, mo):
    # Test review system
    def test_review_system():
        try:
            llm_reviewer_structured = llm.with_structured_output(ReviewOutput)
        
            input_source = "Persistence in LangGraph means keeping state information of the graph throughout its execution."
            initial_quiz = "1. What is life?"
        
            review_prompt = f"""You are a reviewer that scores the quality of quizzes based on input content.
            Consider SOLELY this input below as the source: 
            '''{input_source}.'''
            Now, analyse this quiz created based on the input source:
            '''{initial_quiz}'''. 
            Review this quiz and ONLY return:
            - 'APPROVED' if the quiz is good enough, relevant and it covers well all the important contents of the original material. 
            - 'TO-REVIEW' if the quiz is not relevant to the original material showed above, or not comprehensive enough.
            """
        
            output = llm_reviewer_structured.invoke(review_prompt)
            result = output.quiz_score
        
            display_content = mo.vstack([
                mo.md("# **🎭 Review System Test**"),
                mo.md(f"**Input Source**: {input_source}"),
                mo.md(f"**Quiz**: {initial_quiz}"),
                mo.md(f"**Review Result**: {result}")
            ])
        
            return (llm_reviewer_structured, result, display_content)
        
        except Exception as e:
            display_content = mo.vstack([
                mo.md("# **🎭 Review System Test**"),
                mo.md(f"⚠️ **Error**: {str(e)}")
            ])
        
            return (None, "ERROR", display_content)

    llm_reviewer_structured, review_result, review_test_display = test_review_system()
    review_test_display
    return (llm_reviewer_structured,)


@app.cell
def _(TypedDict, mo):
    # Define quiz state
    def define_quiz_state():
        class QuizState(TypedDict):
            input_source: str
            n_questions: str
            quiz: str
            quiz_quality_score: str
            improved_quiz: str
    
        display_content = mo.vstack([
            mo.md("# **📊 Quiz State Definition**"),
            mo.md(" "),
            mo.md("## **class QuizState(TypedDict):**"),
            mo.md("###    input_source: str"),
            mo.md("###    input_source: str"),
            mo.md("###    input_source: str"),
            mo.md("###    n_questions: str"),
            mo.md("###    quiz: str"),
            mo.md("###    quiz_quality_score: str"),
            mo.md("###    improved_quiz: str"),
            mo.md(" "),
            mo.md("## This state tracks the entire quiz generation and review process.")
        ])
    
        return (QuizState, display_content)

    QuizState, quiz_state_display = define_quiz_state()
    quiz_state_display

    return (QuizState,)


@app.cell
def _(QuizState, llm, llm_reviewer_structured, mo):
    # Define quiz generation nodes
    def define_quiz_nodes():
        def create_quiz(state: QuizState) -> QuizState:
            n_questions = state["n_questions"]
            input_source = state["input_source"]
            quiz = llm.invoke(f"Create a markdown styled quiz with {n_questions} given this content:\n {input_source}")
            return {"quiz": quiz.content}

        def review_quiz(state: QuizState) -> QuizState:
            input_source = state["input_source"]
            initial_quiz = state["quiz"]
            review_prompt = f"""You are a reviewer that scores the quality of quizzes based on input content.
            Consider SOLELY this input below as the source: 
            '''{input_source}.'''
            Now, analyse this quiz created based on the input source:
            '''{initial_quiz}'''. 
            Review this quiz and ONLY return:
            - 'APPROVED' if the quiz is good enough, relevant, has the right number of questions given the input and it
            covers well all the important contents of the original material. 
            - 'TO-REVIEW' if the quiz is not relevant to the original material showed above, or not comprehensive enough.
            """
        
            quiz_quality_score_output = llm_reviewer_structured.invoke(review_prompt)
            quiz_quality_score = quiz_quality_score_output.quiz_score
        
            return {"quiz_quality_score": quiz_quality_score}

        def route_quiz_feedback(state: QuizState) -> str:
            if state["quiz_quality_score"] == "APPROVED":
                return "approved"
            elif state["quiz_quality_score"] == "TO-REVIEW":
                return "improve"

        def write_improved_quiz(state: QuizState) -> QuizState:
            input_source = state["input_source"]
            initial_quiz = state["quiz"]
        
            prompt_improve_quiz = f"""This input was given as the ONLY source: 

            '''{input_source}'''.
            This is the first version of a quiz based only on this source: '''{initial_quiz}'''.
            Write an improved version of this quiz by:
        
            1. Consider 3 points of improvement
            2. Write the improved version of the quiz integrating the feedback
            3. OUTPUT ONLY THE IMPROVED QUIZ AS A NUMBERED LIST."""
        
            improved_quiz = llm.invoke(prompt_improve_quiz)
        
            return {"improved_quiz": improved_quiz.content}
    
        display_content = mo.vstack([
            mo.md("# **🔧 Quiz Generation Nodes**"),
            mo.md("- **create_quiz**: Generates initial quiz from source material"),
            mo.md("- **review_quiz**: Reviews quiz quality and relevance"),
            mo.md("- **route_quiz_feedback**: Routes based on review results"),
            mo.md("- **write_improved_quiz**: Creates improved version if needed")
        ])
    
        return (create_quiz, review_quiz, route_quiz_feedback, write_improved_quiz, display_content)

    create_quiz, review_quiz, route_quiz_feedback, write_improved_quiz, quiz_nodes_display = define_quiz_nodes()
    quiz_nodes_display
    return create_quiz, review_quiz, route_quiz_feedback, write_improved_quiz


@app.cell
def _(
    END,
    QuizState,
    START,
    StateGraph,
    create_quiz,
    mo,
    review_quiz,
    route_quiz_feedback,
    write_improved_quiz,
):
    # Build quiz workflow
    def build_quiz_workflow():
        workflow = StateGraph(QuizState)

        workflow.add_node("create_quiz", create_quiz)
        workflow.add_node("review_quiz", review_quiz)
        workflow.add_node("improve_quiz", write_improved_quiz)

        workflow.add_edge(START, "create_quiz")
        workflow.add_edge("create_quiz", "review_quiz")
        workflow.add_conditional_edges("review_quiz", route_quiz_feedback, {"approved": END, "improve": "improve_quiz"})
        workflow.add_edge("improve_quiz", END)

        graph = workflow.compile()
    
        display_content = mo.vstack([
            mo.md("# **🏗️ Quiz Workflow Built**"),
            mo.md("Workflow includes conditional routing based on quiz quality review.")
        ])
    
        return (graph, display_content)

    quiz_graph, workflow_display = build_quiz_workflow()
    workflow_display
    return (quiz_graph,)


@app.cell
def _(base64, mo, quiz_graph):
    # Display quiz workflow graph
    def display_quiz_graph():
        """Critical: This replaces IPython.display for graph visualization"""
        try:
            png_bytes = quiz_graph.get_graph().draw_mermaid_png()
            img_base64 = base64.b64encode(png_bytes).decode()
        
            html_content = f'''
            <div style="text-align: center; margin: 20px 0;">
                <img src="data:image/png;base64,{img_base64}" 
                     alt="Quiz Workflow Graph" 
                     style="max-width: 600px; height: auto; border: 1px solid #ddd; border-radius: 8px;">
            </div>
            '''
        
            return mo.Html(html_content)
        except Exception as e:
            return mo.md(f"**Error displaying graph**: {str(e)}")

    display_quiz_graph()
    return


@app.cell
def _(mo, quiz_graph):
    # Test quiz generation
    def test_quiz_generation():
        try:
            input_source_raw = """
            1. Persistence in LangGraph means keeping state information of the graph throughout its execution
            2. In LangGraph there are 2 fundamental questions to ask: 1. Which variables to track across the graph's execution 2. Which intermediate artifacts are useful for debugging?
            3. Sub-graphs in langgraph are graphs used as nodes in other graphs (need to share at least 1 key in the state schemas in order to communicate between sub graph and parent graph
            4. Command in Langgraph is a node that works to update state and route to other nodes
            5. Arguments for why a framework like langgraph can be useful:
                * Implementing foundational agentic patterns does not require a framework like LangGraph.
                * LangGraph aims to minimize overhead of implementing these patterns.
                * LangGraph provides supporting infrastructure underneath any workflow/agent.
            """

            output = quiz_graph.invoke({
                "input_source": input_source_raw,
                "n_questions": 5
            })
        
            display_content = mo.vstack([
                mo.md("# **🎯 Quiz Generation Test**"),
                mo.md("**Generated Quiz:**"),
                mo.md(output.get("quiz", "No quiz generated")),
                mo.md(f"**Quality Score**: {output.get('quiz_quality_score', 'Not reviewed')}")
            ])
        
            return (output, display_content)
        
        except Exception as e:
            display_content = mo.vstack([
                mo.md("# **🎯 Quiz Generation Test**"),
                mo.md(f"⚠️ **Error**: {str(e)}")
            ])
        
            return (None, display_content)

    quiz_output, quiz_test_display = test_quiz_generation()
    quiz_test_display
    return


@app.cell
def _(mo):
    # Parallel Pattern Introduction
    def parallel_pattern_introduction():
        return mo.vstack([
            mo.md("# **⚡ Parallel Pattern**"),
            mo.md("The parallel pattern allows multiple LLM calls to execute simultaneously, improving efficiency for independent tasks.")
        ])

    parallel_pattern_introduction()

    return


@app.cell
def _(TypedDict, mo):
    # Define explanation state for parallel pattern
    def define_explanation_state():
        class ExplanationState(TypedDict):
            question: str
            analogy: str
            examples: str
            plain_english: str
            technical_definition: str
            full_explanation: str
    
        display_content = mo.vstack([
            mo.md("# **📊 Explanation State Definition**"),
            mo.md("```python"),
            mo.md("class ExplanationState(TypedDict):"),
            mo.md("    question: str"),
            mo.md("    analogy: str"),
            mo.md("    examples: str"),
            mo.md("    plain_english: str"),
            mo.md("    technical_definition: str"),
            mo.md("    full_explanation: str"),
            mo.md("```"),
            mo.md("This state manages multiple explanation formats generated in parallel.")
        ])
    
        return (ExplanationState, display_content)

    ExplanationState, explanation_state_display = define_explanation_state()
    explanation_state_display

    return


@app.cell
def _(mo):
    # Routing Pattern Introduction
    def routing_pattern_introduction():
        return mo.vstack([
            mo.md("# **🎯 Routing Pattern**"),
            mo.md("Let's look at a simple example of routing between LLMs. We'll create a workflow that:"),
            mo.md("1. Takes a user question"),
            mo.md("2. Routes it to one of three specialized agents:"),
            mo.md("   - Code explanation agent"),
            mo.md("   - Math problem solver"),
            mo.md("   - General knowledge agent"),
            mo.md("3. Gets the specialized response"),
            mo.md("For this example we use structured output to obtain controllable JSON format for routing decisions.")
        ])

    routing_pattern_introduction()

    return


@app.cell
def _(BaseModel, ChatOpenAI, Field, TypedDict, mo):
    # Define routing state and components
    def define_routing_components():
        class RoutingState(TypedDict):
            question: str
            category: str | None
            answer: str | None

        class QuestionType(BaseModel):
            category: str = Field(description="The category classification of the question: CODE or MATH or GENERAL")
    
        openai_llm = ChatOpenAI(model="gpt-4o")
        llm_with_structured_output = openai_llm.with_structured_output(QuestionType)

        # Router that classifies the question
        def route_question(state: RoutingState):
            question = state["question"]
            response = llm_with_structured_output.invoke(
                f"""Classify this question into exactly ONE category:
                - CODE if about programming/coding
                - MATH if about mathematical calculations
                - GENERAL for general knowledge
                Question: {question}
                Category:"""
            )
            return {"category": response.category}

    # Specialized agents
        def code_expert(state: RoutingState):
            return {"answer": openai_llm.invoke(f"As a coding expert, answer: {state['question']}")}

        def math_expert(state: RoutingState):
            return {"answer": openai_llm.invoke(f"As a math expert, solve: {state['question']}")}

        def general_expert(state: RoutingState):
            return {"answer": openai_llm.invoke(f"Answer this general question: {state['question']}")}

        # Define routing logic
        def router(state: RoutingState):
            if state["category"] == "CODE":
                return "code_expert"
            elif state["category"] == "MATH":
                return "math_expert"
            else:
                return "general_expert"
    
        display_content = mo.vstack([
            mo.md("# **🤖 Routing Components Defined**"),
            mo.md("- **RoutingState**: Tracks question, category, and answer"),
            mo.md("- **QuestionType**: Structured output for category classification"),
            mo.md("- **Specialized Agents**: Code, Math, and General experts"),
            mo.md("- **Router Logic**: Directs questions to appropriate expert")
        ])
    
        return (RoutingState, route_question, code_expert, math_expert, general_expert, router, display_content)

    RoutingState, route_question, code_expert, math_expert, general_expert, router, routing_components_display = define_routing_components()
    routing_components_display
        
    return (
        RoutingState,
        code_expert,
        general_expert,
        math_expert,
        route_question,
        router,
    )


@app.cell
def _(
    END,
    RoutingState,
    START,
    StateGraph,
    code_expert,
    general_expert,
    math_expert,
    mo,
    route_question,
    router,
):
    def build_routing_workflow():
        workflow = StateGraph(RoutingState)

        # Add nodes
        workflow.add_node("route", route_question)
        workflow.add_node("code_expert", code_expert)
        workflow.add_node("math_expert", math_expert)
        workflow.add_node("general_expert", general_expert)

        # Add edges
        workflow.add_edge(START, "route")
        workflow.add_conditional_edges(
            "route",
            router,
            {
                "code_expert": "code_expert",
                "math_expert": "math_expert",
                "general_expert": "general_expert"
            }
        )
        workflow.add_edge("code_expert", END)
        workflow.add_edge("math_expert", END)
        workflow.add_edge("general_expert", END)

        graph = workflow.compile()
    
        display_content = mo.vstack([
            mo.md("# **🏗️ Routing Workflow Built**"),
            mo.md("Workflow includes conditional routing based on question classification.")
        ])
    
        return (graph, display_content)

    routing_graph, routing_workflow_display = build_routing_workflow()
    routing_workflow_display

    return (routing_graph,)


@app.cell
def _(base64, mo, routing_graph):
    def display_routing_graph():
        """Critical: This replaces IPython.display for graph visualization"""
        try:
            png_bytes = routing_graph.get_graph().draw_mermaid_png()
            img_base64 = base64.b64encode(png_bytes).decode()
        
            html_content = f'''
            <div style="text-align: center; margin: 20px 0;">
                <img src="data:image/png;base64,{img_base64}" 
                     alt="Routing Workflow Graph" 
                     style="max-width: 600px; height: auto; border: 1px solid #ddd; border-radius: 8px;">
            </div>
            '''
        
            return mo.Html(html_content)
        except Exception as e:
            return mo.md(f"**Error displaying graph**: {str(e)}")


    display_routing_graph()

    return


@app.cell
def _(mo, routing_graph):
    def test_routing_system():
        try:
            result = routing_graph.invoke({
                "question": "What is the time complexity of quicksort?",
                "category": None,
                "answer": None
            })
        
            display_content = mo.vstack([
                mo.md("# **🎯 Routing System Test**"),
                mo.md(f"**Question**: {result['question']}"),
                mo.md(f"**Category**: {result['category']}"),
                mo.md(f"**Answer**: {result['answer'].content if hasattr(result['answer'], 'content') else str(result['answer'])}")
            ])
        
            return (result, display_content)
        
        except Exception as e:
            display_content = mo.vstack([
                mo.md("# **🎯 Routing System Test**"),
                mo.md(f"⚠️ **Error**: {str(e)}")
            ])
        
            return (None, display_content)

    routing_result, routing_test_display = test_routing_system()
    routing_test_display
    return


@app.cell
def _(mo):
    # Summary and key takeaways
    def summary_and_takeaways():
        return mo.vstack([
            mo.md("# **🎯 Key Takeaways**"),
            mo.md("## What we learned:"),
            mo.md("1. **Reducer Functions**: Control how state gets updated in LangGraph"),
            mo.md("2. **Chaining Pattern**: Sequential LLM calls for complex tasks"),
            mo.md("3. **Parallel Pattern**: Simultaneous execution for independent tasks"),
            mo.md("4. **Routing Pattern**: Intelligent routing to specialized agents"),
            mo.md("5. **Structured Output**: Controllable LLM responses for routing decisions"),
            mo.md("## 🚀 Next Steps:"),
            mo.md("- Combine patterns for more complex workflows"),
            mo.md("- Implement error handling and retry logic"),
            mo.md("- Add monitoring and observability"),
            mo.md("- Scale to production environments")
        ])

    summary_and_takeaways()
    return


@app.cell
def _(mo):
    # Reactive Dependencies Diagram - shows how cells interconnect
    def reactive_dependencies_diagram():
        return mo.vstack([
            mo.md("# **🔄 Reactive Dependencies Diagram**"),
            mo.md(" "),
            mo.md("## Visual representation of how cells depend on each other:"),
            mo.md(" "),
            mo.mermaid("""
    graph TD
        C1["Setup Environment<br/>🔑 API Keys"] --> C2["Define MessagesState<br/>📦 State Structure"]
        C1 --> C3["Simple Node<br/>🔧 Basic Example"]
        C1 --> C4["Chaining Introduction<br/>🔗 Pattern Overview"]
        C1 --> C5["Initialize LLMs<br/>🤖 Model Setup"]
        C1 --> C6["Review Structure<br/>📋 Output Format"]
    
        C5 --> C7["Test Review<br/>🎭 System Test"]
        C6 --> C7
        C7 --> C8["Quiz State<br/>📊 State Definition"]
        C8 --> C9["Quiz Nodes<br/>🔧 Workflow Functions"]
        C9 --> C10["Quiz Workflow<br/>🏗️ Build Graph"]
        C10 --> C11["Display Quiz Graph<br/>📊 Visualization"]
        C10 --> C12["Test Quiz Generation<br/>🎯 Live Demo"]
    
        C1 --> C13["Parallel Introduction<br/>⚡ Pattern Overview"]
        C13 --> C14["Explanation State<br/>📊 Parallel State"]
    
        C1 --> C15["Routing Introduction<br/>🎯 Pattern Overview"]
        C15 --> C16["Routing Components<br/>🤖 Agents & Logic"]
        C16 --> C17["Routing Workflow<br/>🏗️ Build Graph"]
        C17 --> C18["Display Routing Graph<br/>📊 Visualization"]
        C17 --> C19["Test Routing<br/>🎯 Live Demo"]
    
        %% Independent cells
        C20["Summary<br/>🎯 Key Takeaways"]
        C21["Dependencies<br/>🔄 This Diagram"]
    
        %% Dark theme friendly styling
        classDef primary fill:#1e3a8a,stroke:#3b82f6,stroke-width:3px,color:#ffffff
        classDef secondary fill:#581c87,stroke:#a855f7,stroke-width:2px,color:#ffffff
        classDef independent fill:#166534,stroke:#22c55e,stroke-width:1px,color:#ffffff
        classDef execution fill:#ea580c,stroke:#f97316,stroke-width:2px,color:#ffffff
        classDef demo fill:#dc2626,stroke:#f87171,stroke-width:2px,color:#ffffff
    
        class C1 primary
        class C5,C8,C9,C10,C16,C17 secondary
        class C2,C3,C4,C6,C13,C14,C15,C20,C21 independent
        class C11,C12,C18,C19 execution
        class C7 demo
            """),
            mo.md(" "),
            mo.md("### 📊 Legend:"),
            mo.md("- **🔵 Primary**: Core foundation (environment setup)"),
            mo.md("- **🟣 Secondary**: Main functionality (states, graphs, workflows)"),
            mo.md("- **🟢 Independent**: Standalone content (explanations, introductions)"),
            mo.md("- **🟠 Execution**: Interactive demonstrations and visualizations"),
            mo.md("- **🔴 Demo**: System testing and validation"),
            mo.md(" "),
            mo.md("### 🎯 Key Insights:"),
            mo.md("- **Environment Setup** is the foundation - all functional cells depend on it"),
            mo.md("- **Three main patterns**: Chaining → Parallel → Routing progression"),
            mo.md("- **Independent cells** can be reordered without breaking dependencies"),
            mo.md("- **Clean separation** between pattern introduction and implementation"),
            mo.md("- **Execution cells** demonstrate working examples of each pattern")
        ])

    reactive_dependencies_diagram()
    return


if __name__ == "__main__":
    app.run()
