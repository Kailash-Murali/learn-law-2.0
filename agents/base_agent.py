"""Base class for all legal agents with XAI traceability."""

import re
import logging as _logging
from typing import Dict, List, Any
from datetime import datetime
from groq import Groq
from config import Config

_logger = _logging.getLogger(__name__)
_verbose: bool = False

# Lazy-initialised Groq client
_groq_client: Groq | None = None


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=Config.GROQ_API_KEY)
    return _groq_client


def _remove_markdown_formatting(text: str) -> str:
    """Remove markdown formatting from text.
    
    Converts:
      **bold** → bold
      *italic* → italic
      # Heading → Heading
      - bullet → bullet
      [link](url) → link
    """
    # Remove bold: **text** → text
    text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
    # Remove italic: *text* → text
    text = re.sub(r'\*([^\*]+)\*', r'\1', text)
    # Remove headings: ### text → text
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # Remove markdown links: [text](url) → text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Clean up code blocks: ```text``` → text
    text = re.sub(r'```([^`]*)```', r'\1', text, flags=re.DOTALL)
    return text


def set_verbose(v: bool) -> None:
    """Enable/disable agent step-level logs."""
    global _verbose
    _verbose = v
    _logging.getLogger("httpx").setLevel(_logging.INFO if v else _logging.WARNING)


class LegalAgent:
    """Base class for legal research agents with XAI traceability"""
    
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        self.reasoning_steps: List[Dict[str, Any]] = []

    def log_reasoning_step(self, step: str, details: Dict[str, Any]):
        """Log a reasoning step for transparency."""
        self.reasoning_steps.append({
            "agent": self.name,
            "step": step,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def call_llm(self, prompt: str, log_reasoning: bool = True) -> str:
        """Call Groq LLM with XAI logging"""
        
        if log_reasoning:
            self.log_reasoning_step(
                "llm_call_initiated",
                {
                    "action": "calling_llm",
                    "prompt_length": len(prompt),
                    "rationale": f"Agent {self.name} requires LLM assistance"
                }
            )
        
        try:
            response = _get_groq_client().chat.completions.create(
                model=Config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            result = response.choices[0].message.content

            if log_reasoning:
                self.log_reasoning_step(
                    "llm_response_received",
                    {
                        "action": "response_processed",
                        "response_length": len(result),
                        "rationale": "LLM provided response successfully"
                    }
                )
            
            return result
        except Exception as e:
            if log_reasoning:
                self.log_reasoning_step(
                    "llm_error",
                    {
                        "action": "error_occurred",
                        "error": str(e),
                        "rationale": "LLM call failed"
                    }
                )
            return f"Error: {str(e)}"
    
    def get_reasoning_trace(self) -> List[Dict[str, Any]]:
        """Get the reasoning trace for this agent"""
        return self.reasoning_steps.copy()
    
    def clear_reasoning_trace(self):
        """Clear the reasoning trace"""
        self.reasoning_steps = []
