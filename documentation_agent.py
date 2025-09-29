from google import genai
from typing import Dict, Any, List
import json
import logging
import datetime
from config import Config
from database import ConstitutionalLawDB
from exceptions import AgentException
import re

def extract_first_json(text: str) -> str:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text

class DocumentationAgent:
    """Documentation Agent for generating presentable JSON output"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.db = ConstitutionalLawDB(self.config.DATABASE_PATH)
        
        # Initialize Gemini
        self.client = genai.Client(api_key=self.config.GEMINI_API_KEY)

        
        self.logger = logging.getLogger(__name__)
    
    def generate_documentation(self, request_id: int) -> Dict[str, Any]:
        """
        Generate structured documentation from research results
        
        Args:
            request_id: Database ID of the research request
            
        Returns:
            Structured JSON suitable for HTML rendering
        """
        try:
            # Get request and research data
            request_data = self.db.get_user_request(request_id)
            research_data = self.db.get_research_results(request_id)
            
            if not request_data or not research_data:
                raise AgentException(f"Missing data for request {request_id}")
            
            # Generate structured documentation using Gemini
            documentation = self._generate_structured_output(request_data, research_data)
            
            # Store documentation in database
            self.db.insert_documentation_output(request_id, documentation)
            
            self.logger.info(f"Documentation generated for request {request_id}")
            return documentation
            
        except Exception as e:
            self.logger.error(f"Documentation generation failed for request {request_id}: {str(e)}")
            raise AgentException(f"Documentation generation failed: {str(e)}")
    
    def _generate_structured_output(self, request_data: Dict[str, Any], 
                                  research_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured documentation using Gemini"""
        
        # Prepare context for Gemini
        context = {
            "original_query": request_data["original_query"],
            "research_topic": request_data["query_summary"]["research_topic"],
            "key_questions": request_data["query_summary"]["key_questions"],
            "legal_concepts": request_data["query_summary"]["legal_concepts"],
            "case_laws": research_data["case_laws"][:5],  # Limit for context
            "statutes": research_data["statutes"][:3],
            "pending_cases": research_data["pending_cases"][:2],
            "articles": research_data["articles"][:3]
        }
        
        prompt = f"""
        As a constitutional law expert, analyze the following research data and create a comprehensive legal research document.
        you are not to give your own opinion in anything, if youre quoting someone, mention it. never assume.
        
        Context: {json.dumps(context, indent=2)}
        
        Generate a structured JSON response with these exact sections:
        
        1. executive_summary: Brief overview of the research findings (2-3 paragraphs)
        2. pending cases: a list of pending cases related to the topic from the research
        3. case_law_review: Analysis of relevant cases with key holdings
        4. statutory_provisions: Review of applicable constitutional provisions
        5. recommendations: Practical recommendations or next steps
        
        Format your response as valid JSON with this structure:
        {{
            "executive_summary": "string",
            "pending_cases": "string", 
            "case_law_review": [
                {{
                    "case_name": "string",
                    "citation": "string", 
                    "key_holding": "string",
                    "relevance": "string"
                }}
            ],
            "statutory_provisions": [
                {{
                    "provision": "string",
                    "text": "string",
                    "application": "string"
                }}
            ],
            "recommendations": [
                "recommendation1",
                "recommendation2",
                "recommendation3"
            ],
            "additional_resources": [
                {{
                    "title": "string",
                    "url": "string", 
                    "description": "string"
                }}
            ]
        }}
        
        Ensure all analysis is legally accurate and professionally formatted. DO NOT include any text outside the JSON structure.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.config.GEMINI_MODEL,
                contents=prompt
            )

            response_text = response.text.strip()
            
            # Clean up markdown formatting if present
            if response_text.startswith("``````"):
                response_text = response_text.replace("``````", "").strip()
            response_text = extract_first_json(response_text)
            
            documentation = json.loads(response_text)
            
            # Add metadata
            documentation["metadata"] = {
                "request_id": request_data["id"],
                "research_topic": request_data["query_summary"]["research_topic"],
                "generated_timestamp": datetime.datetime.now().isoformat(),
                "total_sources": len(research_data.get("sources", [])),
                "total_cases": len(research_data.get("case_laws", [])),
                "total_statutes": len(research_data.get("statutes", []))
            }
            
            return documentation
            
        except json.JSONDecodeError as e:
            # Fallback to basic structure if Gemini response is malformed
            self.logger.warning(f"JSON parsing failed, using fallback structure: {str(e)}")
            return self._create_fallback_documentation(request_data, research_data)
        
        except Exception as e:
            raise AgentException(f"Gemini documentation generation failed: {str(e)}")
    
    def _create_fallback_documentation(self, request_data: Dict[str, Any], 
                                     research_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create basic documentation structure as fallback"""
        
        return {
            "executive_summary": f"Research conducted on: {request_data['query_summary']['research_topic']}. "
                               f"Found {len(research_data.get('case_laws', []))} relevant cases and "
                               f"{len(research_data.get('statutes', []))} statutory provisions.",
            
            "legal_analysis": "Detailed legal analysis could not be generated automatically. "
                            "Please review the case law and statutory provisions below for relevant information.",
            
            "case_law_review": [
                {
                    "case_name": case.get("case_name", "Unknown Case"),
                    "citation": case.get("citation", "No citation available"),
                    "key_holding": case.get("summary", "No summary available"),
                    "relevance": f"Relevance score: {case.get('relevance_score', 'N/A')}"
                }
                for case in research_data.get("case_laws", [])[:5]
            ],
            
            "statutory_provisions": [
                {
                    "provision": statute.get("section", "Unknown Section"),
                    "text": statute.get("text", "No text available"),
                    "application": statute.get("analysis", "No analysis available")
                }
                for statute in research_data.get("statutes", [])[:3]
            ],
            
            "recommendations": [
                "Review the identified case law for precedential value",
                "Analyze statutory provisions for current applicability",
                "Consider consulting with specialized constitutional law counsel"
            ],
            
            "additional_resources": [
                {
                    "title": source.get("title", "Unknown Resource"),
                    "url": source.get("url", "#"),
                    "description": source.get("summary", "Additional research resource")
                }
                for source in research_data.get("sources", [])[:3]
            ],
            
            "metadata": {
                "request_id": request_data["id"],
                "research_topic": request_data["query_summary"]["research_topic"],
                "generated_timestamp": datetime.datetime.now().isoformat(),
                "total_sources": len(research_data.get("sources", [])),
                "total_cases": len(research_data.get("case_laws", [])),
                "total_statutes": len(research_data.get("statutes", [])),
                "fallback_used": True
            }
        }
