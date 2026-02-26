import os
from typing import Dict, Any

from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration settings for the Constitutional Law Research Agent System"""
    
    # Database configuration
    DATABASE_PATH = "constitutional_law.db"
    
    # Gemini API configuration
    GEMINI_API_KEY = "dummy" #os.getenv("GEMINI_API_KEY", "GEMINI_API_KEY")
    GEMINI_MODEL = "gemini-2.0-flash"
    
    # Groq API configuration (FREE, reliable alternative)
    # Get your key from: https://console.groq.com/keys
    GROQ_API_KEY = "dummy"  # Replace with your actual key
    GROQ_MODEL = "llama-3.1-8b-instant"
    
    # in your config.py
    IK_API_TOKEN = "dummmy"

    SPRINGER_META_API_KEY: str = "dummy"
    SPRINGER_OPENACCESS_API_KEY: str = "dummy"

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
