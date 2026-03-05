"""Legal Research Multi-Agent System - Individual Agent Modules

This package organizes agents into separate modules for better modularity and maintainability.
Each agent handles a specific responsibility in the research pipeline.
"""

from .base_agent import LegalAgent, _remove_markdown_formatting
from .ui_agent import UIAgent
from .research_agent import ResearchAgent
from .xai_validation_agent import XAIValidationAgent
from .documentation_agent import DocumentationAgent
from .drafting_agent import DraftingAgent

__all__ = [
    "LegalAgent",
    "_remove_markdown_formatting",
    "UIAgent",
    "ResearchAgent",
    "XAIValidationAgent",
    "DocumentationAgent",
    "DraftingAgent",
]
