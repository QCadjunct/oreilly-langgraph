"""
O'Reilly LangGraph Tutorial Project

This package contains examples and tutorials for learning LangGraph
from the O'Reilly course materials.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Import main function for easy access
from .main import main

# Re-export commonly used components when available
__all__ = ["main"]


# Lazy imports to avoid import errors during installation
def get_langgraph_components():
    """Get LangGraph components if available."""
    try:
        from langgraph.graph import StateGraph
        from langchain_core.messages import BaseMessage
        return {"StateGraph": StateGraph, "BaseMessage": BaseMessage}
    except ImportError:
        return {}
