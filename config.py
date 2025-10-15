import os
from typing import Dict, Any

from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration settings for the Constitutional Law Research Agent System"""
    
    # Database configuration
    DATABASE_PATH = "constitutional_law.db"
    
    # Gemini API configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "GEMINI_API_KEY")
    GEMINI_MODEL = "gemini-2.5-flash"
    # in your config.py
    IK_API_TOKEN = "abbb21b37c3bbc1458ae370c7cae561720e50a87"

    SPRINGER_META_API_KEY: str = "cfbab3fb1ac671d4b411e034375edd54"
    SPRINGER_OPENACCESS_API_KEY: str = "1adc3c130fae757475f10ef16013f0bb"

    # Legal API placeholders (to be implemented)
    LEGAL_APIS = {
        "courtlistener": {
            "base_url": "https://www.courtlistener.com/api/rest/v3/",
            "api_key": os.getenv("COURTLISTENER_API_KEY", "placeholder-key")
        },
        "justia": {
            "base_url": "https://law.justia.com/api/",
            "api_key": os.getenv("JUSTIA_API_KEY", "placeholder-key")
        }
    }
    
    # Qdrant configuration (mock for now)
    QDRANT_CONFIG = {
        "host": "localhost",
        "port": 6333,
        "collection_name": "constitutional_law_docs"
    }
    
    # Agent configuration
    AGENT_CONFIG = {
        "max_retries": 3,
        "retry_delay": 1.0,
        "timeout": 30.0
    }
