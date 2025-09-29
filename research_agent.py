from google import genai
import asyncio
from typing import Dict, Any, List
import json
import logging
from ik_api_async import AsyncIKApi
from config import Config
from database import ConstitutionalLawDB
from exceptions import AgentException, APIException
import re

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

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.db = ConstitutionalLawDB(self.config.DATABASE_PATH)
        self.client = genai.Client(api_key=self.config.GEMINI_API_KEY)
        self.logger = logging.getLogger(__name__)
        self.ikapi = AsyncIKApi(self.config.IK_API_TOKEN)


    async def conduct_research(self, request_id: int) -> Dict[str, Any]:
        try:
            request_data = self.db.get_user_request(request_id)
            if not request_data:
                raise AgentException(f"Request {request_id} not found")
            query_summary = request_data['query_summary']
            self.logger.info(f"Starting research for request {request_id}")

            # Step 1: Use Gemini to decide tool usage & queries
            tool_plan = self._get_tool_plan(query_summary)

            # Step 2: For each tool/query, call mock function and gather results
            research_tasks = [
                self._case_law_api(tool_plan.get('case_law_query')),
                self._statute_api(tool_plan.get('statute_query')),
                self._pending_case_api(tool_plan.get('pending_case_query')),
                self._mock_article_api(tool_plan.get('article_query')),  # Remains mock for now
                self._mock_rag_search(tool_plan.get('rag_query')),       # RAG: do later
            ]
            print("Case Law Query: ", tool_plan.get('case_law_query'))
            print("Statute Query: ", tool_plan.get('statute_query'))
            print("Pending Case Query: ", tool_plan.get('pending_case_query'))
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
            return research_data

        except Exception as e:
            self.logger.error(f"Research failed for request {request_id}: {str(e)}")
            raise AgentException(f"Research failed: {str(e)}")

    def _get_tool_plan(self, query_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Uses Gemini to decide which tools/queries to use for this research request.
        Returns dict with queries for each tool.
        """
        prompt = f"""
            You are an expert legal research agent. Given a user research request, generate queries to retrieve information using the Indian Kanoon API.

            **IMPORTANT GUIDELINES:**
            - ALWAYS use concise legal keywords, case names, major statutes (e.g. 'article 21', 'Maneka Gandhi'), or quoted legal phrases (e.g. "personal liberty", "freedom of speech").
            - DO NOT generate conversational or natural language questions.
            - Use Indian Kanoon API logical operators: ANDD, ORR, NOTT, for combining/negating words.
            - For **case law**, target judgments and major case names, e.g. formInput='"article 21" ANDD "right to life"'.
            - For **statutes**, target Indian acts/rules, e.g. formInput='"Protection of Women from Domestic Violence Act"'.
            - For **pending cases**, use recent terms, keywords, or phrases related to ongoing matters.
            - For **articles**, use concise legal topics or phrases; leave blank if not relevant.
            - If the request references recent cases, specify 'fromdate' or 'todate' fields (in DD-MM-YYYY).
            - Suggest appropriate 'doctypes' (e.g. judgments, acts, highcourts).
            - Return empty string "" if a tool is not relevant for this query.
            - Your response must be STRICTLY valid JSON, do NOT include extraneous commentary or formatting outside JSON.

            **User Research Request:**  
            {json.dumps(query_summary, indent=2)}

            **Your output:**  
            {{
            "case_law_query": "Indian Kanoon search string and filters (quotes/ANDD/ORR/NOTT/doctype if needed)",
            "statute_query": "search string and filters for statute retrieval",
            "pending_case_query": "search string and filters for ongoing/pending cases",
            "article_query": "topic or keywords for legal commentary or leave blank",
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
        return tool_plan

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
