from google import genai
import asyncio
from typing import Dict, Any, List, Optional, Tuple
import json
import logging
from ik_api_async import AsyncIKApi
from config import Config
from database import ConstitutionalLawDB
from exceptions import AgentException, APIException
from trace_logger import TraceLogger
import re
from springer import SpringerLegalResearch, SpringerConfig

def extract_first_json(text: str) -> str:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text
def extract_query_string(tool_plan_value: str) -> str:
    if isinstance(tool_plan_value, dict) and 'formInput' in tool_plan_value:
        return tool_plan_value['formInput']
    s = tool_plan_value.strip()
    s = re.sub(r"^formInput\s*=\s*", "", s)
    s = re.sub(r"doctypes\s*=\s*[\w,]+", "", s)
    s = re.sub(r"(author|bench|year|title|cite)\s*=\s*[\w\s\"\'-]+", "", s)
    s = s.strip(" \n\r\"'")
    return s.strip()

class ResearchAgent:
    """Research Agent using Gemini AI to orchestrate all research tools"""

    def __init__(self, config: Config = None, db: Optional[ConstitutionalLawDB] = None,
                 trace_logger: Optional[TraceLogger] = None):
        self.config = config or Config()
        self.db = db or ConstitutionalLawDB(self.config.DATABASE_PATH)
        self.trace_logger = trace_logger
        self.client = genai.Client(api_key=self.config.GEMINI_API_KEY)
        self.logger = logging.getLogger(__name__)
        self.ikapi = AsyncIKApi(self.config.IK_API_TOKEN)
        springer_config = SpringerConfig(
            meta_api_key=self.config.SPRINGER_META_API_KEY,
            openaccess_api_key=self.config.SPRINGER_OPENACCESS_API_KEY,
            results_per_page=15,
            max_results=20,
            enable_openaccess=True
        )
        self.springer = SpringerLegalResearch(springer_config)


    async def conduct_research(self, request_id: int) -> Dict[str, Any]:
        try:
            request_data = self.db.get_user_request(request_id)
            if not request_data:
                raise AgentException(f"Request {request_id} not found")
            query_summary = request_data['query_summary']
            self.logger.info(f"Starting research for request {request_id}")

            # Step 1: Use Gemini to decide tool usage & queries
            tool_plan, raw_plan = self._get_tool_plan(query_summary)

            normalized_queries = {
                "case_law": extract_query_string(tool_plan.get('case_law_query', '') or ''),
                "statute": extract_query_string(tool_plan.get('statute_query', '') or ''),
                "pending": extract_query_string(tool_plan.get('pending_case_query', '') or ''),
                "articles": extract_query_string(tool_plan.get('article_query', '') or ''),
                "rag": extract_query_string(tool_plan.get('rag_query', '') or ''),
            }

            if self.trace_logger:
                self.trace_logger.snapshot_artefact(
                    agent="ResearchAgent",
                    artefact_type="tool_plan",
                    content={"raw_response": raw_plan, "plan": tool_plan},
                    request_id=request_id,
                )
                self.trace_logger.record_decision(
                    agent="ResearchAgent",
                    decision_type="tool_plan",
                    metadata={
                        "normalized_queries": normalized_queries,
                        "original_plan": tool_plan,
                    },
                    request_id=request_id,
                    rationale="Prepared deterministic search queries for external tools.",
                )

            # Step 2: For each tool/query, call mock function and gather results
            research_tasks = [
                self._case_law_api(tool_plan.get('case_law_query')),
                self._statute_api(tool_plan.get('statute_query')),
                self._pending_case_api(tool_plan.get('pending_case_query')),
                self._springer_article_api(tool_plan.get('article_query')),  # Real Springer API
                self._mock_rag_search(tool_plan.get('rag_query')),       # RAG: do later
            ]
            print("Case Law Query: ", tool_plan.get('case_law_query'))
            print("Statute Query: ", tool_plan.get('statute_query'))
            print("Pending Case Query: ", tool_plan.get('pending_case_query'))
            print("Article Query: ", tool_plan.get('article_query'))
            results = await asyncio.gather(*research_tasks, return_exceptions=True)
            research_data = {
                'case_laws': results[0] if not isinstance(results[0], Exception) else [],
                'statutes': results[1] if not isinstance(results[1], Exception) else [],
                'pending_cases': results[2] if not isinstance(results[2], Exception) else [],
                'articles': results[3] if not isinstance(results[3], Exception) else [],
                'sources': results[4] if not isinstance(results[4], Exception) else []
            }

            # Store in database
            self.db.insert_research_results(request_id, research_data)
            self.logger.info(f"Research completed for request {request_id}")
            if self.trace_logger:
                self.trace_logger.snapshot_artefact(
                    agent="ResearchAgent",
                    artefact_type="research_results",
                    content={
                        "results": research_data,
                        "queries": normalized_queries,
                    },
                    request_id=request_id,
                )
                self.trace_logger.log_event(
                    agent="ResearchAgent",
                    event_type="results_persisted",
                    payload={
                        "case_laws": len(research_data.get('case_laws', [])),
                        "statutes": len(research_data.get('statutes', [])),
                        "articles": len(research_data.get('articles', [])),
                    },
                    request_id=request_id,
                    phase="research",
                )
            return research_data

        except Exception as e:
            self.logger.error(f"Research failed for request {request_id}: {str(e)}")
            if self.trace_logger:
                self.trace_logger.log_event(
                    agent="ResearchAgent",
                    event_type="error",
                    payload={"error": str(e)},
                    request_id=request_id,
                    phase="research",
                )
            raise AgentException(f"Research failed: {str(e)}")

    def _get_tool_plan(self, query_summary: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """
        Uses Gemini to decide which tools/queries to use for this research request.
        Returns dict with queries for each tool.
        """
        prompt = f"""
                You are an expert legal research agent. Given a user research request, generate queries for TWO different systems:
                1. Indian Kanoon API (for Indian case law, statutes, pending cases)
                2. Springer Nature API (for academic articles and scholarly commentary)

                **INDIAN KANOON QUERIES:**
                - Use concise legal keywords, case names, major statutes (e.g. 'article 21', 'Maneka Gandhi')
                - Use quoted legal phrases (e.g. "personal liberty", "freedom of speech")
                - Use Indian Kanoon logical operators: ANDD, ORR, NOTT
                - For **case law**: Target judgments, e.g. '"article 21" ANDD "right to life"'
                - For **statutes**: Target Indian acts, e.g. '"Protection of Women from Domestic Violence Act"'
                - For **pending cases**: Use recent terms/keywords for ongoing matters

                **SPRINGER NATURE QUERIES (CRITICAL RULES):**
                - Use ONLY 2-3 keywords maximum
                - Use specific legal terminology that uniquely identifies law topics
                - GOOD examples (self-evidently legal, no ambiguity):
                * "constitutional rights India"
                * "judicial review"
                * "Article 21"
                * "fundamental rights"
                * "separation of powers"
                * "rule of law India"
                - BAD examples (too generic, will match non-legal articles):
                * "human rights law" (matches medical papers about humans)
                * "privacy law" (matches tech/engineering papers)
                * "equality law" (matches physics/math papers)
                * "law" (way too broad)
                - **KEY INSIGHT**: Words like "human", "rights", "privacy", "freedom", "equality" appear in science/tech papers too!
                Instead use: "constitutional", "judicial", "statute", "Article [number]", "Supreme Court"
                - If the topic is inherently ambiguous, make it specific:
                * Instead of "privacy law" → "constitutional privacy India"
                * Instead of "human rights law" → "fundamental rights India"
                * Instead of "equality law" → "constitutional equality"
                - Return empty string "" if scholarly articles are not relevant

                **GENERAL RULES:**
                - Return empty string "" for any tool not relevant to this query
                - Your response must be STRICTLY valid JSON only
                - DO NOT include commentary, markdown, or formatting outside JSON

                **User Research Request:**  
                {json.dumps(query_summary, indent=2)}

                **Your output (MUST be valid JSON):**  
                {{
                "case_law_query": "Indian Kanoon search for judgments",
                "statute_query": "Indian Kanoon search for statutes/acts",
                "pending_case_query": "Indian Kanoon search for pending cases",
                "article_query": "2-3 SPECIFIC legal keywords (use constitutional/judicial terms, not generic terms)",
                "rag_query": "semantic search phrase for database"
                }}
                """

        response = self.client.models.generate_content(
            model=self.config.GEMINI_MODEL,
            contents=prompt
        )
        response_text = response.text.strip()
        if response_text.startswith("``````"):
            response_text = response_text.replace("``````", "").strip()
        response_text = extract_first_json(response_text)
        tool_plan = json.loads(response_text)
        return tool_plan, response_text

    async def _case_law_api(self, query: str):
        # judgments doctype for case law
        case_query = extract_query_string(query)
        results = await self.ikapi.search(case_query, doctype="judgments", maxpages=1)
        docs = results.get("docs", [])
        return [
            {
                "case_name": doc.get("title"),
                "citation": doc.get("citation", ""),
                "summary": doc.get("snippet", ""),
                "court": doc.get("docsource"),
                "publishdate": doc.get("publishdate"),
                "url": f"https://indiankanoon.org/doc/{doc['tid']}/" if "tid" in doc else None
            }
            for doc in docs
        ]

    async def _statute_api(self, query: str):
        statute_query = extract_query_string(query)

        results = await self.ikapi.search(statute_query, doctype="acts", maxpages=1)
        docs = results.get("docs", [])
        return [
            {
                "section": doc.get("title"),
                "text": doc.get("snippet", ""),
                "court": doc.get("docsource"),
                "date": doc.get("publishdate"),
                "url": f"https://indiankanoon.org/doc/{doc['tid']}/" if "tid" in doc else None
            }
            for doc in docs
        ]

    async def _pending_case_api(self, query: str):
        # No explicit "pending" flag, you may use date filtering if needed
        pending_query = extract_query_string(query)

        results = await self.ikapi.search(pending_query, maxpages=1)
        docs = results.get("docs", [])
        return [
            {
                "case_name": doc.get("title"),
                "court": doc.get("docsource"),
                "publishdate": doc.get("publishdate"),
                "url": f"https://indiankanoon.org/doc/{doc['tid']}/" if "tid" in doc else None
            }
            for doc in docs
        ]
    
    async def _springer_article_api(self, query: str) -> List[Dict[str, Any]]:
        """
        Search Springer Nature for academic articles.
        Uses Meta API for broader coverage.
        """
        if not query or query.strip() == "":
            return []
        
        try:
            article_query = extract_query_string(query)
            
            # Search using Springer Meta API (Basic plan compatible)
            results = await self.springer.search_meta(
                query=article_query,
                filters=None,  # No filters for now, can add later
                use_basic_plan=True  # IMPORTANT: You have Basic plan
            )
            
            self.logger.info(f"Springer returned {len(results)} articles for query: {article_query}")
            return results
            
        except Exception as e:
            self.logger.error(f"Springer API failed: {str(e)}")
            return []  # Return empty on failure, don't break the whole research
    # ---- MOCK/Fake tool implementations below ----
    async def _mock_case_law_api(self, query: str) -> List[Dict[str, Any]]:
        await asyncio.sleep(0.2)
        return [
            {
                "case_name": "Mock v. Reality",
                "citation": "123 U.S. 456",
                "summary": f"Case law found for query '{query}'",
                "relevance_score": 0.95,
                "key_holdings": ["Legal mock principle"],
                "url": "https://supreme.justia.com/mock/reality"
            }
        ]

    async def _mock_statute_api(self, query: str) -> List[Dict[str, Any]]:
        await asyncio.sleep(0.1)
        return [
            {
                "section": "MockConst. § 7",
                "title": "Mock Statute Result",
                "text": f"Statute for query '{query}'",
                "relevance_score": 0.88,
                "analysis": "Mock statute analysis"
            }
        ]

    async def _mock_pending_case_api(self, query: str) -> List[Dict[str, Any]]:
        await asyncio.sleep(0.1)
        return [
            {
                "case_name": "Pending v. Decided",
                "court": "Mock Supreme Court",
                "status": "Pending",
                "summary": f"Pending case for query '{query}'",
                "relevance_score": 0.9,
                "docket_number": "MOCK-2021",
                "key_issues": ["Mock Issue"]
            }
        ]

    async def _mock_article_api(self, query: str) -> List[Dict[str, Any]]:
        await asyncio.sleep(0.15)
        return [
            {
                "title": "Mock Article on Law",
                "authors": ["Jane Fake", "Mike Pretend"],
                "journal": "Law Review",
                "year": 2024,
                "abstract": f"Article for query '{query}'",
                "relevance_score": 0.87,
                "url": "https://mock.legal/article"
            }
        ]

    async def _mock_rag_search(self, query: str) -> List[Dict[str, Any]]:
        await asyncio.sleep(0.1)
        return [
            {
                "url": "https://mockragdb.org/resource",
                "title": "Mock RAG Result",
                "relevance_score": 0.85,
                "content_type": "educational_resource",
                "summary": f"RAG DB result for query '{query}'"
            }
        ]
