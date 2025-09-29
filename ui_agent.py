from google import genai
from typing import Dict, Any, Optional, List, Tuple
import json
import logging
from datetime import datetime

from config import Config
from database import ConstitutionalLawDB
from exceptions import AgentException, ValidationException
from trace_logger import TraceLogger
import re

def extract_first_json(text: str) -> str:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text

class UIAgent:
    """UI Agent for processing user input and converting to structured JSON"""

    def __init__(self, config: Config = None, db: Optional[ConstitutionalLawDB] = None,
                 trace_logger: Optional[TraceLogger] = None):
        self.config = config or Config()
        self.db = db or ConstitutionalLawDB(self.config.DATABASE_PATH)
        self.trace_logger = trace_logger
        self.client = genai.Client(api_key=self.config.GEMINI_API_KEY)
        self.logger = logging.getLogger(__name__)

    def process_user_input(self, user_id: str, query: str) -> Dict[str, Any]:
        """Process natural language user input and convert to structured JSON"""
        try:
            structured_query, raw_response = self._structure_query_with_gemini(query)
            self._validate_structured_query(structured_query)
            request_id = self.db.insert_user_request(
                user_id=user_id,
                original_query=query,
                query_summary=structured_query
            )
            self.logger.info(f"Processed user input for request {request_id}")
            if self.trace_logger:
                self.trace_logger.snapshot_artefact(
                    agent="UIAgent",
                    artefact_type="structured_query",
                    content={
                        "original_query": query,
                        "structured_query": structured_query,
                        "raw_response": raw_response,
                    },
                    request_id=request_id,
                )
                self.trace_logger.log_event(
                    agent="UIAgent",
                    event_type="structured_query_generated",
                    payload={"fields": list(structured_query.keys())},
                    request_id=request_id,
                    phase="ui_processing",
                )
                self.trace_logger.record_decision(
                    agent="UIAgent",
                    decision_type="query_structuring",
                    metadata=structured_query,
                    request_id=request_id,
                    rationale="Converted natural language into research template fields.",
                )
            return {
                "request_id": request_id,
                "structured_query": structured_query,
                "status": "pending",
                "raw_response": raw_response,
            }
        except Exception as e:
            self.logger.error(f"Error processing user input: {str(e)}")
            if self.trace_logger:
                self.trace_logger.log_event(
                    agent="UIAgent",
                    event_type="error",
                    payload={"error": str(e)},
                    phase="ui_processing",
                )
            raise AgentException(f"Failed to process user input: {str(e)}")

    def _structure_query_with_gemini(self, query: str) -> Tuple[Dict[str, Any], str]:
        """Use Gemini to convert natural language to structured JSON"""
        prompt = f"""
        You are a constitutional law expert. Convert the following user query into structured JSON format for legal research.

        User Query: "{query}"

        Extract and structure the following information:
        1. research_topic: Main constitutional law topic or issue
        2. key_questions: List of specific legal questions to research
        3. legal_concepts: Relevant constitutional principles, amendments, or doctrines
        4. scope: Research scope (federal, state, historical period, etc.)

        Respond ONLY with valid JSON in this exact format:
        {{
            "research_topic": "string",
            "key_questions": ["question1", "question2", ...],
            "legal_concepts": ["concept1", "concept2", ...],
            "scope": "string"
        }}

        DO NOT include any text outside the JSON structure.
        """
        try:
            response = self.client.models.generate_content(
                model=self.config.GEMINI_MODEL,
                contents=prompt
            )
            response_text = response.text.strip()
            if response_text.startswith("``````"):
                response_text = response_text.replace("``````", "").strip()
            response_text = extract_first_json(response_text)
            structured_data = json.loads(response_text)
            return structured_data, response_text
        except json.JSONDecodeError as e:
            raise AgentException(f"Failed to parse Gemini response as JSON: {str(e)}")
        except Exception as e:
            raise AgentException(f"Gemini API error: {str(e)}")

    def _validate_structured_query(self, query: Dict[str, Any]):
        """Validate the structured query format"""
        required_fields = ['research_topic', 'key_questions', 'legal_concepts', 'scope']
        for field in required_fields:
            if field not in query:
                raise ValidationException(f"Missing required field: {field}")
        if not isinstance(query['key_questions'], list):
            raise ValidationException("key_questions must be a list")
        if not isinstance(query['legal_concepts'], list):
            raise ValidationException("legal_concepts must be a list")

    def generate_clarifying_questions(self, query: str) -> List[str]:
        """Generate clarifying questions for ambiguous queries"""
        prompt = f"""
        As a constitutional law expert, analyze this query and generate 2-3 clarifying questions 
        to better understand the user's research needs.

        User Query: "{query}"

        Focus on:
        - Specific constitutional provisions or amendments
        - Jurisdictional scope (federal vs state)
        - Time period of interest
        - Type of analysis needed (historical, current application, etc.)

        Return only a JSON array of strings:
        ["question1", "question2", "question3"]
        """
        try:
            response = self.client.models.generate_content(
                model=self.config.GEMINI_MODEL,
                contents=prompt
            )
            response_text = response.text.strip()
            if response_text.startswith("``````"):
                response_text = response_text.replace("``````", "").strip()
            response_text = extract_first_json(response_text)
            questions = json.loads(response_text)
            return questions
        except Exception as e:
            self.logger.error(f"Error generating clarifying questions: {str(e)}")
            return ["Could you specify which constitutional amendment or provision you're interested in?"]
