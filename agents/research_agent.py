"""ResearchAgent - Conducts legal research."""

import logging as _logging
from typing import Dict, Any

from .base_agent import LegalAgent, _remove_markdown_formatting, _verbose

_logger = _logging.getLogger(__name__)


class ResearchAgent(LegalAgent):
    """Conducts legal research with XAI transparency"""
    
    def __init__(self):
        super().__init__(
            name="ResearchAgent",
            system_prompt="""You are an expert legal researcher specializing EXCLUSIVELY in Indian Constitutional Law.

Your job is to:
1. Find relevant case laws with proper citations (case name, year, court).
2. Cite specific Indian statutes with their FULL official name and year —
   e.g., "The Information Technology Act, 2000" or "The Protection of Human Rights Act, 1993".
3. Mention the relevant constitutional Article or Section for every claim.
4. Summarize key holdings and principles from Indian case law.

STATUTE RULES — CRITICAL:
- ALWAYS include at least one statute or legislative act if it is relevant.
- ONLY cite statutes that are currently in force. NEVER cite:
    * Section 66A of the IT Act, 2000 — struck down (Shreya Singhal v. UoI, 2015)
    * Section 124A IPC (Sedition) — prosecutions stayed by SC since 2022
    * TADA (lapsed 1995) or POTA (repealed 2004)
    * Any provision explicitly repealed or struck down by the Supreme Court.
- If a topic involves a struck-down provision, say it was struck down and cite the case.

IMPORTANT: ONLY Indian law. No other jurisdiction.

Always provide well-researched, accurate information with proper citations from Indian legal sources.""")
    
    def research(self, parsed_query: Dict[str, Any], feedback_ctx: str = "") -> Dict[str, Any]:
        """Conduct legal research based on parsed query with XAI logging.

        Parameters
        ----------
        feedback_ctx : str
            LLM-friendly string with past user complaints so the model
            can avoid repeating the same mistakes.
        """
        if _verbose:
            print(f"🔍 {self.name}: Conducting research...")
        
        # Validate jurisdiction - only Indian jurisdiction allowed
        if parsed_query.get("error") == "jurisdiction_not_supported":
            return {
                "error": "jurisdiction_not_supported",
                "message": parsed_query.get("message", "Sorry, I can only answer questions related to Indian jurisdiction."),
                "query_info": parsed_query,
                "status": "rejected"
            }
        
        jurisdiction = parsed_query.get("jurisdiction", "India").lower()
        if jurisdiction and "india" not in jurisdiction:
            self.log_reasoning_step(
                "jurisdiction_validation_failed",
                {
                    "action": "rejecting_non_indian_jurisdiction",
                    "jurisdiction": parsed_query.get("jurisdiction", ""),
                    "rationale": "Research agent only supports Indian legal jurisdiction"
                }
            )
            return {
                "error": "jurisdiction_not_supported",
                "message": "Sorry, I can only answer questions related to Indian jurisdiction.",
                "query_info": parsed_query,
                "status": "rejected"
            }
        
        # Log research strategy selection
        self.log_reasoning_step(
            "research_strategy_selection",
            {
                "action": "selecting_research_approach",
                "topic": parsed_query.get("topic", ""),
                "jurisdiction": parsed_query.get("jurisdiction", "India"),
                "rationale": "Choosing appropriate research methodology based on query characteristics",
                "alternatives": "Could use different databases, API sources, or search strategies"
            }
        )
        
        prompt = f"""
Research the following legal topic:

Topic: {parsed_query.get('topic', '')}
Jurisdiction: {parsed_query.get('jurisdiction', 'India')}
Keywords: {', '.join(parsed_query.get('keywords', []))}

Provide:
1. Relevant constitutional articles/provisions
2. Key case laws with citations (case name, year, court)
3. Important legal principles established
4. Any relevant statutes

Format your response as detailed legal research.

IMPORTANT: Do NOT use markdown formatting (**bold**, *italic*, etc). Use plain text only.{feedback_ctx}"""

        response = self.call_llm(prompt)
        
        # Remove markdown formatting from response (belt-and-suspenders approach)
        response = _remove_markdown_formatting(response)
        
        # Log research completion
        self.log_reasoning_step(
            "research_completed",
            {
                "action": "research_results_compiled",
                "response_length": len(response),
                "sources_used": ["Indian Kanoon", "Supreme Court Judgments", "Constitutional Provisions"],
                "rationale": "Research completed using constitutional law knowledge base"
            }
        )
        
        return {
            "query_info": parsed_query,
            "research_content": response,
            "sources": ["Indian Kanoon", "Supreme Court Judgments", "Constitutional Provisions"],
            "status": "completed",
            "reasoning_trace": self.get_reasoning_trace()
        }
