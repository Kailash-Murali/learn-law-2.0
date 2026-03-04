import os
import getpass
import logging
from typing import Dict, Any, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _get_secret(env_var: str, prompt: str | None = None, required: bool = True) -> str:
    """
    Load a secret with priority: env-var → interactive getpass → empty string.

    - NEVER logs or prints the secret value.
    - In non-interactive environments (e.g. CI/server) falls back to empty string
      so the caller can decide what to do.
    """
    value = os.getenv(env_var, "").strip()
    if value:
        return value

    # Interactive fallback
    if prompt and os.isatty(0):
        try:
            value = getpass.getpass(prompt).strip()
            if value:
                return value
        except (EOFError, KeyboardInterrupt):
            pass

    if required:
        logger.warning("Secret %s is not set. Set the %s environment variable.", env_var, env_var)
    return ""


class Config:
    """Configuration settings for the Constitutional Law Research Agent System"""

    # Database configuration
    DATABASE_PATH = "constitutional_law.db"

    GROQ_API_KEY: str = _get_secret(
        "GROQ_API_KEY", prompt="Enter Groq API key (https://console.groq.com/keys): "
    )
    GROQ_MODEL = "llama-3.1-8b-instant"

    IK_API_TOKEN: str = _get_secret(
        "IK_API_TOKEN", prompt="Enter Indian Kanoon API token: "
    )

    SPRINGER_META_API_KEY: str = _get_secret(
        "SPRINGER_META_API_KEY", prompt="Enter Springer Meta API key: "
    )
    SPRINGER_OPENACCESS_API_KEY: str = _get_secret(
        "SPRINGER_OPENACCESS_API_KEY", prompt="Enter Springer OpenAccess API key: "
    )

    # Qdrant configuration (mock for now)
    QDRANT_CONFIG = {
        "host": "localhost",
        "port": 6333,
        "collection_name": "constitutional_law_docs",
    }

    # Agent configuration
    AGENT_CONFIG = {
        "max_retries": 3,
        "retry_delay": 1.0,
        "timeout": 30.0,
    }

    @classmethod
    def validate(cls) -> list[str]:
        """Return a list of missing-but-required secret names."""
        required = [
            "GROQ_API_KEY",
            "IK_API_TOKEN",
        ]
        return [name for name in required if not getattr(cls, name, "")]
