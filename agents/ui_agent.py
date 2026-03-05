"""UIAgent - Query parsing and user input structuring."""

import json
import logging as _logging
from typing import Dict, Any

from .base_agent import LegalAgent, _verbose

_logger = _logging.getLogger(__name__)


class UIAgent(LegalAgent):
    """Parses and structures user queries with XAI transparency"""
    
    def __init__(self):
        super().__init__(
            name="UIAgent",
            system_prompt="""You are a legal query parser for INDIAN LAW ONLY. Your job is to:
1. Understand the user's legal research query
2. Extract key topics, jurisdictions, and keywords
3. Return a structured JSON response

IMPORTANT: This system ONLY handles Indian jurisdiction. If a query asks about any other country's laws (USA, UK, etc.), 
set jurisdiction to that country name so it can be rejected.

Always respond with valid JSON in this format:
{
    "topic": "main legal topic",
    "jurisdiction": "India" (or the actual country if non-Indian law is asked),
    "keywords": ["keyword1", "keyword2"],
    "document_types": ["case_law", "statutes", "articles"],
    "time_period": "any specific time constraints"
}

If no jurisdiction is mentioned in the query, default to "India"."""
        )
    
    def parse(self, query: str) -> Dict[str, Any]:
        """Parse user query into structured format with XAI logging"""
        if _verbose:
            print(f"📝 {self.name}: Parsing query...")
        
        # Log reasoning step
        self.log_reasoning_step(
            "query_analysis_started",
            {
                "action": "analyzing_user_query",
                "query_length": len(query),
                "rationale": "Need to extract structured information from natural language query",
                "alternatives": "Could use regex-based extraction or direct keyword matching"
            }
        )
        
        prompt = f"Parse this legal research query:\n\n{query}"
        response = self.call_llm(prompt)
        
        try:
            # Try to extract JSON from response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            elif "{" in response:
                start = response.index("{")
                end = response.rindex("}") + 1
                json_str = response[start:end]
            else:
                json_str = response
            
            result = json.loads(json_str)
            
            # Validate jurisdiction - only Indian jurisdiction allowed
            jurisdiction = result.get("jurisdiction", "").lower()
            if jurisdiction and "india" not in jurisdiction:
                self.log_reasoning_step(
                    "jurisdiction_validation_failed",
                    {
                        "action": "rejecting_non_indian_jurisdiction",
                        "detected_jurisdiction": result.get("jurisdiction", ""),
                        "rationale": "System only supports Indian legal jurisdiction"
                    }
                )
                return {
                    "error": "jurisdiction_not_supported",
                    "message": "Sorry, I can only answer questions related to Indian jurisdiction.",
                    "detected_jurisdiction": result.get("jurisdiction", ""),
                    "topic": result.get("topic", ""),
                    "keywords": result.get("keywords", [])
                }
            
            # Log successful parsing
            self.log_reasoning_step(
                "query_parsed_successfully",
                {
                    "action": "json_extraction_success",
                    "extracted_topic": result.get("topic", ""),
                    "keyword_count": len(result.get("keywords", [])),
                    "rationale": "Successfully extracted structured query information"
                }
            )
            
            return result
        except Exception as e:
            # Log parsing failure
            self.log_reasoning_step(
                "query_parsing_fallback",
                {
                    "action": "using_default_structure",
                    "error": str(e),
                    "rationale": "JSON parsing failed, using fallback extraction method"
                }
            )
            
            # Return default structure if parsing fails
            return {
                "topic": query,
                "jurisdiction": "India",
                "keywords": query.split()[:5],
                "document_types": ["case_law", "statutes"],
                "time_period": "all"
            }
