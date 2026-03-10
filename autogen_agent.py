"""
AutoGen-based Legal Research Multi-Agent System

This module implements the legal research workflow using AutoGen
for agent coordination, with Groq as the LLM backend.
"""

from typing import Dict, List, Any, Optional
import json
import re
import uuid
import asyncio
import logging as _logging
from datetime import datetime
import requests
from groq import Groq
from config import Config
from springer_agent import SpringerAgent, set_verbose as set_springer_verbose
from agents.xai_validation_agent import XAIValidationAgent
from agents.documentation_agent import DocumentationAgent
from agents.drafting_agent import DraftingAgent

# Suppress httpx HTTP-request logs by default (shown only when --logs is active)
_logging.getLogger("httpx").setLevel(_logging.WARNING)

# Module-level verbosity flag — toggled via set_verbose() each run
_verbose: bool = False

# ── Feedback loop ──────────────────────────────────────────────────────
FEEDBACK_FILE = "feedback_log.jsonl"


def load_feedback_context(max_entries: int = 10) -> str:
    """Read recent user feedback and return an LLM-friendly context string.

    Returns an empty string when there is no feedback file or no entries.
    """
    import os
    if not os.path.isfile(FEEDBACK_FILE):
        return ""
    lines: list[str] = []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as fh:
            for raw_line in fh:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    entry = json.loads(raw_line)
                    q   = entry.get("query", "")
                    iss = entry.get("issue", "")
                    if q or iss:
                        lines.append(f"- Query: {q} | User complaint: {iss}")
                except json.JSONDecodeError:
                    continue
    except Exception:
        return ""
    if not lines:
        return ""
    recent = lines[-max_entries:]
    return (
        "\n\n[CRITICAL — PREVIOUS USER FEEDBACK] You MUST follow these feedback items to improve your answers:\n"
        + "\n".join(recent)
        + "\n\n[MANDATORY FIXES]\n"
        + "1. Do NOT use markdown formatting (** **) in your output — use plain text instead\n"
        + "2. Avoid **bold**, *italic*, or other markdown symbols\n"
        + "3. Keep formatting clean, simple, and readable\n"
    )


def set_verbose(v: bool) -> None:
    """Enable/disable agent step-level logs and httpx request logs."""
    global _verbose
    _verbose = v
    _logging.getLogger("httpx").setLevel(_logging.INFO if v else _logging.WARNING)


# Lazy-initialised Groq client – avoid import-time API-key validation
_groq_client: Groq | None = None


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=Config.GROQ_API_KEY)
    return _groq_client


def _remove_markdown_formatting(text: str) -> str:
    """Remove markdown formatting from text.
    
    Converts:
      **bold** → bold
      *italic* → italic
      # Heading → Heading
      - bullet → bullet
      [link](url) → link
    """
    # Remove bold: **text** → text
    text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
    # Remove italic: *text* → text
    text = re.sub(r'\*([^\*]+)\*', r'\1', text)
    # Remove headings: ### text → text
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # Remove markdown links: [text](url) → text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Clean up code blocks: ```text``` → text
    text = re.sub(r'```([^`]*)```', r'\1', text, flags=re.DOTALL)
    return text


class LegalAgent:
    """Base class for legal research agents with XAI traceability"""
    
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        self.reasoning_steps: List[Dict[str, Any]] = []

    def log_reasoning_step(self, step: str, details: Dict[str, Any]):
        """Log a reasoning step for transparency."""
        self.reasoning_steps.append({
            "agent": self.name,
            "step": step,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def call_llm(self, prompt: str, log_reasoning: bool = True) -> str:
        """Call Groq LLM with XAI logging"""
        
        if log_reasoning:
            self.log_reasoning_step(
                "llm_call_initiated",
                {
                    "action": "calling_llm",
                    "prompt_length": len(prompt),
                    "rationale": f"Agent {self.name} requires LLM assistance"
                }
            )
        
        try:
            response = _get_groq_client().chat.completions.create(
                model=Config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            result = response.choices[0].message.content

            if log_reasoning:
                self.log_reasoning_step(
                    "llm_response_received",
                    {
                        "action": "response_processed",
                        "response_length": len(result),
                        "rationale": "LLM provided response successfully"
                    }
                )
            
            return result
        except Exception as e:
            if log_reasoning:
                self.log_reasoning_step(
                    "llm_error",
                    {
                        "action": "error_occurred",
                        "error": str(e),
                        "rationale": "LLM call failed"
                    }
                )
            return f"Error: {str(e)}"
    
    def get_reasoning_trace(self) -> List[Dict[str, Any]]:
        """Get the reasoning trace for this agent"""
        return self.reasoning_steps.copy()
    
    def clear_reasoning_trace(self):
        """Clear the reasoning trace"""
        self.reasoning_steps = []


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


class UIFormatter:
    """Deterministic transformer that converts the raw pipeline result dict
    into a structured JSON payload designed for the Next.js frontend.

    This is NOT an LLM agent — it performs a purely mechanical mapping.
    """

    @staticmethod
    def format(result: Dict[str, Any]) -> Dict[str, Any]:
        """Return a frontend-friendly JSON structure.

        The payload is designed so the Next.js UI can render each section
        without any further parsing:
          • answer / draft text
          • validation badge (grounded / risk label / risk score)
          • citations array  [{name, url, verified}]
          • statutes array   [{name, url, verified}]
          • bad_laws array   [{law, reason}]
          • article_refs     [str]
          • flags            [str]
          • feedback_id      str
        """
        doc = result.get("documentation", {})
        val = result.get("validation", {})

        risk = val.get("hallucination_risk", 0)
        risk_label = "LOW" if risk < 0.35 else "MEDIUM" if risk < 0.65 else "HIGH"

        # Build citations list
        citations: List[Dict[str, Any]] = []
        for case, url in val.get("citation_links", {}).items():
            citations.append({"name": case, "url": url, "verified": url is not None})

        # Build statutes list
        statutes: List[Dict[str, Any]] = []
        for statute, url in val.get("statute_links", {}).items():
            statutes.append({"name": statute, "url": url, "verified": url is not None})

        # Academic papers from Springer (populated when want_research=True)
        springer_papers = result.get("research", {}).get("springer_papers", [])

        # Determine content type and text
        doc_type = doc.get("type", "simple_answer")
        if doc_type == "legal_draft":
            content = doc.get("draft", "")
            content_type = "draft"
        elif doc_type == "full_report":
            content = doc.get("full_report", "")
            content_type = "report"
        else:
            content = doc.get("answer", "")
            content_type = "answer"

        return {
            "content_type": content_type,
            "content": content,
            "draft_type": doc.get("draft_type"),
            "draft_description": doc.get("draft_description"),
            "executive_summary": doc.get("executive_summary"),
            "validation": {
                "is_grounded": val.get("is_grounded", False),
                "risk_label": risk_label,
                "risk_score": risk,
                "ik_available": val.get("ik_available", False),
                "feedback_id": val.get("feedback_id"),
                "citations": citations,
                "statutes": statutes,
                "bad_laws": val.get("bad_laws_found", []),
                "article_refs": val.get("article_refs", []),
                "flags": val.get("flags", []),
            },
            "pdf_path": result.get("pdf_path"),
            "springer_papers": springer_papers,
            "contrastive": result.get("contrastive", {}),
        }


class Coordinator:
    """Coordinates the multi-agent workflow with XAI traceability"""

    def __init__(self):
        self.ui_agent = UIAgent()
        self.research_agent = ResearchAgent()
        self.xai_validation_agent = XAIValidationAgent()
        self.documentation_agent = DocumentationAgent()
        self.drafting_agent = DraftingAgent()
        self.springer_agent = SpringerAgent()
        self.ui_formatter = UIFormatter()
        self.workflow_trace: List[Dict[str, Any]] = []
        self.springer_results: Dict[str, Any] = {}

    def _log_workflow_step(self, step: str, agent: str, details: Dict[str, Any]):
        """Log a workflow step for XAI transparency"""
        self.workflow_trace.append({
            "step": step,
            "agent": agent,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def run(
        self,
        query: str,
        want_report: bool = False,
        want_pdf: bool = False,
        want_draft: str | None = None,
        show_logs: bool = False,
        want_research: bool = False,
        want_contrastive: bool = False
    ) -> Dict[str, Any]:
        """Run the complete research workflow.

        Parameters
        ----------
        want_report : generate a full structured report instead of a concise answer
        want_pdf    : generate a full report AND save it as a PDF file
        want_draft  : generate a legal draft of the given type
                      (e.g. "writ_petition", "legal_notice", "rti", "complaint", "affidavit")
        show_logs   : print agent step logs and httpx request logs
        want_research : enable academic paper research from Springer
        """
        set_verbose(show_logs)
        set_springer_verbose(show_logs)

        # Clear previous traces
        self.workflow_trace = []
        self.ui_agent.clear_reasoning_trace()
        self.research_agent.clear_reasoning_trace()
        self.xai_validation_agent.clear_reasoning_trace()
        self.documentation_agent.clear_reasoning_trace()
        self.drafting_agent.clear_reasoning_trace()

        result = {
            "query": query,
            "parsed_query": {},
            "research": {},
            "validation": {},
            "documentation": {},
            "pdf_path": None,
            "status": "started",
            "error": None,
            "workflow_trace": [],
            "agent_reasoning_traces": {},
            "springer_results": {}
        }

        try:
            # ── Step 1: Parse Query ──────────────────────────────────────
            self._log_workflow_step("query_parsing", "UIAgent", {"query": query})

            result["parsed_query"] = self.ui_agent.parse(query)

            if result["parsed_query"].get("error") == "jurisdiction_not_supported":
                result["status"] = "rejected"
                result["error"] = result["parsed_query"].get(
                    "message", "Sorry, I can only answer questions related to Indian jurisdiction."
                )
                print(f"❌ {result['error']}\n")
                return result

            if show_logs:
                print(f"✅ Query parsed: {result['parsed_query'].get('topic', query)}\n")

            # ── Load past user feedback for context ─────────────────────
            feedback_ctx = load_feedback_context()
            if feedback_ctx and show_logs:
                print("📝 Injecting past user feedback into research context\n")

            # ── Step 2: Conduct Research ─────────────────────────────────
            self._log_workflow_step("research_execution", "ResearchAgent",
                                    {"topic": result["parsed_query"].get("topic", "")})

            result["research"] = self.research_agent.research(
                result["parsed_query"], feedback_ctx=feedback_ctx
            )
            if show_logs:
                print("✅ Research completed\n")

            # ── Step 2a: Springer Academic Search (optional augmentation, if --research) ───
            if want_research:
                self._log_workflow_step("springer_search", "SpringerAgent",
                                        {"topic": result["parsed_query"].get("topic", "")})
                
                parsed_keywords = result["parsed_query"].get("keywords", [])
                springer_result = self.springer_agent.search(
                    query=result["parsed_query"].get("topic", query),
                    topic_keywords=parsed_keywords
                )
                self.springer_results = springer_result
                
                if show_logs and springer_result["total_papers"] > 0:
                    print(f"✅ Springer search completed: {springer_result['total_papers']} academic papers found\n")
                elif show_logs:
                    print("⚠️  Springer search: No papers found (this is okay)\n")

                # Augment research with Springer academic papers
                if springer_result["total_papers"] > 0:
                    springer_formatted = self.springer_agent.format_results_for_research()
                    result["research"]["research_content"] = (
                        result["research"]["research_content"] + "\n" + springer_formatted
                    )
                    result["research"]["springer_papers"] = springer_result["combined_papers"]
                    result["research"]["has_academic_papers"] = True
                else:
                    result["research"]["has_academic_papers"] = False
            else:
                result["research"]["has_academic_papers"] = False

            # ── Step 3: XAI Validation ───────────────────────────────────
            self._log_workflow_step("xai_validation", "XAIValidationAgent",
                                    {"research_available": True})

            if show_logs:
                print(f"🔎 {self.xai_validation_agent.name}: Validating research...")
            result["validation"] = self.xai_validation_agent.validate(query, result["research"])
            if show_logs:
                feedback_id = result["validation"].get("feedback_id", "N/A")
                risk = result["validation"].get("hallucination_risk", 0)
                risk_label = "LOW" if risk < 0.35 else "MEDIUM" if risk < 0.65 else "HIGH"
                print(f"✅ Validation complete — Hallucination risk: {risk_label} "
                      f"| Citations: {len(result['validation'].get('citations_found', []))} "
                      f"| Feedback ID: {feedback_id}\n")

            # Use validated content for the documentation step
            research_for_doc = result["research"].copy()
            validated_content = result["validation"].get("validated_content", "")
            if validated_content:
                research_for_doc["validated_content"] = validated_content

            # ── Step 4: Documentation / Drafting ───────────────────────
            if want_draft:
                # ── Step 4a: Legal Draft ──────────────────────────────────
                self._log_workflow_step("draft_generation", "DraftingAgent",
                                        {"draft_type": want_draft})
                if show_logs:
                    print(f"📝 DraftingAgent: Generating {want_draft} ...")
                result["documentation"] = self.drafting_agent.generate_draft(
                    query, research_for_doc, want_draft
                )
                # Generate Word document for the draft
                try:
                    docx_path = self.drafting_agent.generate_docx(
                        result["documentation"]["draft"], query, want_draft
                    )
                    result["docx_path"] = docx_path
                    if show_logs and docx_path:
                        print(f"✅ DOCX saved: {docx_path}")
                except Exception as exc:
                    _logging.getLogger(__name__).warning("DOCX generation failed: %s", exc)
                if show_logs:
                    print("✅ Draft generated\n")
            elif want_report or want_pdf:
                self._log_workflow_step("documentation_generation", "DocumentationAgent",
                                        {"want_report": want_report, "want_pdf": want_pdf})
                result["documentation"] = self.documentation_agent.generate_report(
                    query, research_for_doc
                )
                if want_pdf:
                    if show_logs:
                        print("📑 Generating PDF...")
                    pdf_path = self.documentation_agent.generate_pdf(
                        result["documentation"]["full_report"], query
                    )
                    result["pdf_path"] = pdf_path
                    if show_logs:
                        if pdf_path:
                            print(f"✅ PDF saved: {pdf_path}\n")
                        else:
                            print("⚠️  PDF generation failed — reportlab may not be installed.\n")
                elif show_logs:
                    print("✅ Full report generated\n")
            else:
                result["documentation"] = self.documentation_agent.generate_simple_answer(
                    query, research_for_doc
                )
                if show_logs:
                    print("✅ Answer generated\n")

            # ── Step 4b: Contrastive / counterfactual XAI (only when requested) ────
            if want_contrastive:
                try:
                    result["contrastive"] = self.documentation_agent.generate_counterfactuals(
                        query, research_for_doc
                    )
                except Exception as _cf_exc:
                    _logging.getLogger(__name__).warning("Counterfactual analysis failed: %s", _cf_exc)
                    result["contrastive"] = {}
            else:
                result["contrastive"] = {}

            result["status"] = "completed"

            # ── Step 5: UI formatting (deterministic, no LLM) ────────────
            result["ui_payload"] = self.ui_formatter.format(result)

            # Collect reasoning traces
            result["workflow_trace"] = self.workflow_trace
            result["springer_results"] = self.springer_results
            result["agent_reasoning_traces"] = {
                "UIAgent": self.ui_agent.get_reasoning_trace(),
                "ResearchAgent": self.research_agent.get_reasoning_trace(),
                "XAIValidationAgent": self.xai_validation_agent.get_reasoning_trace(),
                "DocumentationAgent": self.documentation_agent.get_reasoning_trace(),
                "DraftingAgent": self.drafting_agent.get_reasoning_trace(),
            }

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            print(f"❌ Error: {e}\n")

        return result


class AutoGenLegalResearch:
    """Main interface for the legal research system."""

    def __init__(self):
        self.coordinator = Coordinator()

    def run_research(self, query: str, want_report: bool = False, want_pdf: bool = False,
                     want_draft: str | None = None,
                     show_logs: bool = False, want_research: bool = False,
                     want_contrastive: bool = False) -> Dict[str, Any]:
        """Run research — concise answer by default; full report/PDF/draft on request."""
        return self.coordinator.run(
            query,
            want_report=want_report,
            want_pdf=want_pdf,
            want_draft=want_draft,
            show_logs=show_logs,
            want_research=want_research,
            want_contrastive=want_contrastive,
        )

    def parse_query(self, query: str) -> Dict[str, Any]:
        """Parse query only."""
        return self.coordinator.ui_agent.parse(query)

    def conduct_research(self, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct research only."""
        return self.coordinator.research_agent.research(parsed_query)

    def generate_documentation(self, query: str, parsed_query: Dict, research: Dict) -> Dict[str, Any]:
        """Generate a simple answer (default) from research."""
        return self.coordinator.documentation_agent.generate_simple_answer(query, research)


def run_autogen_research(query: str) -> Dict[str, Any]:
    """Convenience function to run research."""
    return AutoGenLegalResearch().run_research(query)


if __name__ == "__main__":
    query = "What are the fundamental rights under Article 21 of Indian Constitution?"
    result = run_autogen_research(query)
    print("\n" + "=" * 60)
    print(f"Status: {result['status']}")
    print("=" * 60)
    if result.get("documentation"):
        print(result["documentation"].get("answer", ""))
    if result.get("error"):
        print(f"\n❌ Error: {result['error']}")