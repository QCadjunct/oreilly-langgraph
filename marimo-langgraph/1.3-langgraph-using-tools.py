import marimo as mo

__generated_with = "0.14.7"
app = mo.App()

import base64

# Global imports - all defined here for maximum DRY
import getpass
import os
from typing import Annotated, TypedDict

from IPython.display import Image, Markdown, display
from langchain_ollama import ChatOllama, OllamaLLM
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import AnyMessage, add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

mo.md("# **State as Messages - LangGraph Tutorial**")
mo.md(
    "This notebook demonstrates how to use LangGraph with tools, specifically using the `add_messages` function to add messages to the state. This is a simple example that shows how to use LangGraph with tools, specifically using the `add_messages` function to add messages to the state."
)
