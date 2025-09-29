import asyncio
import logging
from typing import Dict, Any, Optional

from config import Config
from database import ConstitutionalLawDB
from ui_agent import UIAgent
from research_agent import ResearchAgent
from documentation_agent import DocumentationAgent
from exceptions import AgentException

class MainAgent:
    """Main orchestration agent that coordinates all other agents"""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.db = ConstitutionalLawDB(self.config.DATABASE_PATH)
        self.ui_agent = UIAgent(self.config)
        self.research_agent = ResearchAgent(self.config)
        self.documentation_agent = DocumentationAgent(self.config)
        self.logger = logging.getLogger(__name__)

    async def process_request(self, user_id: str, query: str) -> Dict[str, Any]:
        request_id = None
        try:
            # Step 1: Process user input with UI Agent
            self.logger.info("Starting request processing")
            ui_result = self.ui_agent.process_user_input(user_id, query)
            request_id = ui_result["request_id"]

            # Step 2: Update status to researching
            self.db.update_request_status(request_id, "researching")

            # Step 3: Conduct research (with retry)
            research_data = await self._conduct_research_with_retry(request_id)

            # Step 4: Update status to documenting
            self.db.update_request_status(request_id, "documenting")

            # Step 5: Generate documentation (with retry)
            documentation = await self._generate_documentation_with_retry(request_id)

            # Step 6: Update status to completed
            self.db.update_request_status(request_id, "completed")

            return {
                "request_id": request_id,
                "status": "completed",
                "structured_query": ui_result["structured_query"],
                "research_data": research_data,
                "documentation": documentation,
                "processing_summary": {
                    "total_cases_found": len(research_data.get("case_laws", [])),
                    "total_statutes_found": len(research_data.get("statutes", [])),
                    "total_articles_found": len(research_data.get("articles", [])),
                    "research_sources": len(research_data.get("sources", []))
                }
            }

        except Exception as e:
            error_msg = f"Request processing failed: {str(e)}"
            self.logger.error(error_msg)
            if request_id:
                try:
                    self.db.update_request_status(request_id, "failed")
                except:
                    pass
            raise AgentException(error_msg)

    async def _conduct_research_with_retry(self, request_id: int) -> Dict[str, Any]:
        max_retries = getattr(self.config, "MAX_RETRIES", 3)
        retry_delay = getattr(self.config, "RETRY_DELAY", 1)
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Research attempt {attempt + 1} for request {request_id}")
                return await self.research_agent.conduct_research(request_id)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                self.logger.warning(f"Research attempt {attempt + 1} failed: {str(e)}")
                await asyncio.sleep(retry_delay * (2 ** attempt))
        raise AgentException("Research failed after all retry attempts")

    async def _generate_documentation_with_retry(self, request_id: int) -> Dict[str, Any]:
        max_retries = getattr(self.config, "MAX_RETRIES", 3)
        retry_delay = getattr(self.config, "RETRY_DELAY", 1)
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Documentation attempt {attempt + 1} for request {request_id}")
                return self.documentation_agent.generate_documentation(request_id)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                self.logger.warning(f"Documentation attempt {attempt + 1} failed: {str(e)}")
                await asyncio.sleep(retry_delay * (2 ** attempt))
        raise AgentException("Documentation generation failed after all retry attempts")

    def get_request_status(self, request_id: int) -> Optional[Dict[str, Any]]:
        try:
            request_data = self.db.get_user_request(request_id)
            if not request_data:
                return None
            result = {
                "request_id": request_id,
                "status": request_data["status"],
                "timestamp": request_data["timestamp"],
                "research_topic": request_data["query_summary"]["research_topic"]
            }
            if request_data["status"] in ["documenting", "completed"]:
                research_data = self.db.get_research_results(request_id)
                if research_data:
                    result["research_summary"] = {
                        "cases_found": len(research_data.get("case_laws", [])),
                        "statutes_found": len(research_data.get("statutes", [])),
                        "articles_found": len(research_data.get("articles", []))
                    }
            if request_data["status"] == "completed":
                doc_data = self.db.get_documentation_output(request_id)
                if doc_data:
                    result["documentation_available"] = True
            return result
        except Exception as e:
            self.logger.error(f"Error getting request status: {str(e)}")
            return None

    def get_completed_documentation(self, request_id: int) -> Optional[Dict[str, Any]]:
        try:
            doc_data = self.db.get_documentation_output(request_id)
            return doc_data["output_json"] if doc_data else None
        except Exception as e:
            self.logger.error(f"Error retrieving documentation: {str(e)}")
            return None
