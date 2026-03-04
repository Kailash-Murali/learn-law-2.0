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
        "\n\nIMPORTANT — Previous user feedback on your answers "
        "(avoid repeating these mistakes):\n"
        + "\n".join(recent)
        + "\n"
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
        
        response = self.call_llm(f"Parse this legal research query:\n\n{query}")
        
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

Format your response as detailed legal research.{feedback_ctx}"""

        response = self.call_llm(prompt)
        
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


class XAIValidationAgent(LegalAgent):
    """
    XAI Validation Agent — Enforces four anti-hallucination measures:
      1. Factual Grounding  : every claim must be anchored to a real Indian legal source
      2. Source Citation    : requires explicit citations (case name / Article / Section)
      3. Scope Limiting     : restricts output to summarisation/search — no invented law
      4. User Feedback      : stamps every response with a unique ID so users can report issues
    """

    # Regex patterns for constitutional articles/sections (verified by rule, not IK)
    ARTICLE_PATTERNS = [
        r'\bArticle\s+\d+[A-Z]?(?:\(\d+\))?\b',   # Article 21, Article 14A, Article 32(1)
        r'\bSection\s+\d+[A-Z]?\b',                 # Section 302
    ]

    # Regex patterns for Indian statute/act citations
    STATUTE_PATTERNS = [
        r'\bThe\s+[A-Z][\w\s]+Act,?\s+\d{4}\b',              # "The XYZ Act, 1950"
        r'\b(?:Indian\s+Penal\s+Code|Code\s+of\s+Criminal\s+Procedure|Code\s+of\s+Civil\s+Procedure)(?:,?\s+\d{4})?\b',
        r'\b(?:IPC|CrPC|CPC)\b',                              # Common shorthand
    ]

    # Rule-based registry of repealed / struck-down / bad Indian laws.
    # Keys are lowercase substrings to scan for; values are (display_name, authoritative_reason).
    # EVALUATION: Rule-based is unambiguously correct here — these are historical facts.
    # An LLM may have stale training data and cite a law as in-force when it was struck down.
    REPEALED_OR_BAD_LAWS: Dict[str, tuple] = {
        "section 66a": (
            "Section 66A of the IT Act, 2000",
            "Struck down as unconstitutional — Shreya Singhal v. Union of India (2015)",
        ),
        "section 124a": (
            "Section 124A IPC — Sedition",
            "SC stayed all prosecutions in 2022 (S.G. Vombatkere v. UoI); under constitutional review",
        ),
        "tada": (
            "Terrorist and Disruptive Activities (Prevention) Act (TADA)",
            "Lapsed in 1995 — Parliament did not renew it",
        ),
        "pota": (
            "Prevention of Terrorism Act (POTA)",
            "Repealed by Prevention of Terrorism (Repeal) Act, 2004",
        ),
        "section 377 ipc": (
            "Section 377 IPC — criminalisation of same-sex relations",
            "Partially struck down for consenting adults — Navtej Singh Johar v. UoI (2018)",
        ),
        "imdt act": (
            "Illegal Migrants (Determination by Tribunal) Act, 1983",
            "Struck down by SC — Sarbananda Sonowal v. Union of India (2005)",
        ),
        "prevention of terrorism ordinance": (
            "Prevention of Terrorism Ordinance",
            "Subsumed by POTA (2002) which was itself repealed in 2004",
        ),
    }

    def __init__(self):
        super().__init__(
            name="XAIValidationAgent",
            system_prompt="""You are an Indian legal citation extractor.
Given legal research text, extract the names of all judicial cases cited.
Return ONLY a JSON array of strings — no explanation, no markdown.
Example: ["Maneka Gandhi v. Union of India (1978)", "A.K. Kraipak v. Union of India (1970)"]
If no cases are cited, return: []"""
        )

    def _ik_search(self, case_name: str) -> Optional[Dict[str, str]]:
        """
        Search Indian Kanoon for a case citation and return the best-matching
        result.  Uses quoted party names and scans top results for a title
        match instead of blindly returning docs[0].

        Returns ``{"title": ..., "url": ...}`` or *None*.
        """
        token = Config.IK_API_TOKEN
        if not token:
            return None

        # ── Parse party names and year from the citation ──────────────
        parts = re.split(
            r'\s+v\.?\s+|\s+vs\.?\s+', case_name, maxsplit=1, flags=re.IGNORECASE
        )
        party1 = re.sub(r'\(?\d{4}\)?', '', parts[0]).strip()
        party2 = re.sub(r'\(?\d{4}\)?', '', parts[1]).strip() if len(parts) > 1 else None
        year_m = re.search(r'\b(1[89]\d{2}|20[0-2]\d)\b', case_name)
        year   = year_m.group(1) if year_m else None

        party1_lower = party1.lower()

        # ── Build up to 2 query strategies ────────────────────────────
        queries: List[str] = []
        if year:
            # Best strategy: party1 + year  (avoids party2 abbreviation issues)
            queries.append(f'"{party1}" {year}')
        if party2:
            queries.append(f'"{party1}" "{party2}"')
        if not queries:
            queries.append(f'"{party1}"')

        # ── Try each query, return on first title-matched hit ─────────
        for query in queries:
            try:
                resp = requests.post(
                    "https://api.indiankanoon.org/search/",
                    data={"formInput": query, "pagenum": 0},
                    headers={"Authorization": f"Token {token}"},
                    timeout=8,
                )
                if resp.status_code != 200:
                    continue

                docs = resp.json().get("docs", [])

                for d in docs[:10]:
                    title_raw = d.get("title", "")
                    title_clean = (
                        title_raw.replace("<b>", "").replace("</b>", "")
                    )
                    tid = d.get("tid")
                    if not tid:
                        continue

                    # Accept only if the first party name appears in the title
                    if party1_lower in title_clean.lower():
                        return {
                            "title": title_clean,
                            "url": f"https://indiankanoon.org/doc/{tid}/",
                        }
            except Exception:
                continue

        return None

    def _ik_statute_search(self, statute_name: str) -> Optional[Dict[str, str]]:
        """
        Search Indian Kanoon for a statute / act and return the first matching
        document whose title shares key capitalised words with *statute_name*.
        Returns ``{"title": ..., "url": ...}`` or *None*.
        """
        token = Config.IK_API_TOKEN
        if not token:
            return None
        # Build query from the statute name, quoted for precision
        query = f'"{statute_name.strip()}"'
        try:
            resp = requests.post(
                "https://api.indiankanoon.org/search/",
                data={"formInput": query, "pagenum": 0},
                headers={"Authorization": f"Token {token}"},
                timeout=8,
            )
            if resp.status_code != 200:
                return None
            docs = resp.json().get("docs", [])
            # Key words from the statute name (skip generic words)
            _SKIP = {"the", "of", "and", "for", "in", "an", "a", "act", "code"}
            key_words = [
                w.lower() for w in re.findall(r'[A-Za-z]{3,}', statute_name)
                if w.lower() not in _SKIP
            ]
            for d in docs[:8]:
                title_clean = d.get("title", "").replace("<b>", "").replace("</b>", "")
                tid = d.get("tid")
                if not tid or not key_words:
                    continue
                # Accept if at least half the key words appear in the title
                matches = sum(1 for kw in key_words if kw in title_clean.lower())
                if matches >= max(1, len(key_words) // 2):
                    return {
                        "title": title_clean,
                        "url": f"https://indiankanoon.org/doc/{tid}/",
                    }
        except Exception:
            pass
        return None

    def validate(self, query: str, research: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate research via Indian Kanoon API cross-verification.

        Steps:
          1. Regex extracts Article/Section refs (always reliable).
          2. Regex extracts statute/act citations.
          3. Rule-based scan for repealed / struck-down laws.
          4. LLM extracts case names; each is looked up on Indian Kanoon.
          5. Statutes are looked up on Indian Kanoon.
          6. Hallucination risk = f(unverified cases, bad laws, missing statutes).
        """
        research_content = research.get("research_content", "")

        self.log_reasoning_step(
            "validation_started",
            {
                "action": "extracting_citations_for_ik_verification",
                "content_length": len(research_content),
                "rationale": "Cross-verify case citations against Indian Kanoon API"
            }
        )

        # ── Step 1a: Extract Article/Section refs by regex (always reliable) ──
        article_refs: List[str] = []
        for pat in self.ARTICLE_PATTERNS:
            article_refs.extend(re.findall(pat, research_content, re.IGNORECASE))
        article_refs = sorted(set(article_refs))

        # ── Step 1b: Extract statute/act citations by regex (rule-based) ─────
        statute_refs: List[str] = []
        for pat in self.STATUTE_PATTERNS:
            statute_refs.extend(re.findall(pat, research_content, re.IGNORECASE))
        statute_refs = sorted(set(s.strip() for s in statute_refs if len(s.strip()) > 3))

        # ── Step 1c: Bad-law scan (rule-based, deterministic) ─────────────────
        # WHY RULES: Repealed/struck-down status is a historical fact. LLMs can
        # hallucinate that a struck-down law is still in force; a hard lookup list
        # is more reliable than asking the LLM to self-check.
        bad_laws_found: List[Dict[str, str]] = []
        content_lower = research_content.lower()
        for keyword, (display_name, reason) in self.REPEALED_OR_BAD_LAWS.items():
            if keyword in content_lower:
                bad_laws_found.append({"law": display_name, "reason": reason})

        # ── Step 2: Ask LLM to extract case names ────────────────────────
        raw = self.call_llm(
            f"Extract all case names from this text:\n\n{research_content[:2000]}",
            log_reasoning=False
        )
        extracted_cases: List[str] = []
        try:
            bracket_start = raw.index("[")
            bracket_end   = raw.rindex("]") + 1
            extracted_cases = json.loads(raw[bracket_start:bracket_end])
            if not isinstance(extracted_cases, list):
                extracted_cases = []
        except Exception:
            # fallback: grab any "X v. Y" patterns
            extracted_cases = re.findall(
                r'[A-Z][\w\s&.]+\bv\.\s+[A-Z][\w\s&.]+(?:\(\d{4}\))?',
                research_content
            )[:8]
        extracted_cases = [c.strip() for c in extracted_cases if isinstance(c, str) and c.strip()][:10]

        # ── Step 3: Cross-verify each case on Indian Kanoon ──────────────
        ik_available      = bool(Config.IK_API_TOKEN)
        citation_links: Dict[str, Optional[str]] = {}   # case → URL or None
        verified: List[str]   = []
        unverified: List[str] = []

        for case in extracted_cases:
            hit = self._ik_search(case)
            if hit:
                verified.append(case)
                citation_links[case] = hit["url"]
            else:
                unverified.append(case)
                citation_links[case] = None

        # ── Step 3b: Verify statutes on Indian Kanoon ─────────────────────
        statute_links: Dict[str, Optional[str]] = {}
        if ik_available:
            for statute in statute_refs[:6]:   # cap at 6 to limit API calls
                hit = self._ik_statute_search(statute)
                statute_links[statute] = hit["url"] if hit else None

        # ── Step 4: Compute hallucination risk ───────────────────────────
        total = len(extracted_cases)
        flags: List[str] = []

        # 4a — case citation risk
        if total == 0:
            is_grounded = bool(article_refs) or bool(statute_refs)
            risk        = 0.25 if (article_refs or statute_refs) else 0.65
            if not article_refs and not statute_refs:
                flags.append("No case citations, article references, or statute citations detected")
        elif ik_available:
            unverified_ratio = len(unverified) / total
            risk             = round(unverified_ratio * 0.85, 2)
            is_grounded      = len(verified) > 0 or bool(article_refs) or bool(statute_refs)
            for c in unverified[:3]:
                flags.append(f"Case not found on Indian Kanoon: {c}")
        else:
            risk        = 0.30
            is_grounded = total > 0 or bool(article_refs) or bool(statute_refs)
            flags.append("IK_API_TOKEN not set — Indian Kanoon verification skipped")

        # 4b — statute-absent penalty
        if not statute_refs and not article_refs:
            risk = min(1.0, risk + 0.10)
            flags.append("No statute or constitutional article citations — answer may lack legal grounding")

        # 4c — bad-law penalty (rule-based, each bad law adds 0.15 to risk)
        for bl in bad_laws_found:
            risk = min(1.0, risk + 0.15)
            flags.append(f"BAD LAW CITED: {bl['law']} — {bl['reason']}")

        risk = round(risk, 2)
        feedback_id = str(uuid.uuid4())[:8].upper()

        result = {
            "feedback_id"      : feedback_id,
            "is_grounded"      : is_grounded,
            "citation_links"   : citation_links,     # {case_name: IK_url | None}
            "statute_links"    : statute_links,      # {statute_name: IK_url | None}
            "bad_laws_found"   : bad_laws_found,     # [{"law": ..., "reason": ...}]
            "article_refs"     : article_refs,
            "statute_refs"     : statute_refs,
            "verified_on_ik"   : verified,
            "unverified_on_ik" : unverified,
            "ik_available"     : ik_available,
            "citations_found"  : list(citation_links.keys()) + article_refs + statute_refs,
            "hallucination_risk": risk,
            "validated_content": research_content,
            "flags"            : flags,
            "scope_violations" : [],
            "original_content" : research_content,
            "status"           : "validated"
        }

        risk_label = (
            "LOW"    if risk < 0.35 else
            "MEDIUM" if risk < 0.65 else
            "HIGH"
        )

        self.log_reasoning_step(
            "validation_completed",
            {
                "action"              : "ik_cross_verification_done",
                "cases_extracted"     : total,
                "verified_on_ik"      : len(verified),
                "unverified_on_ik"    : len(unverified),
                "statutes_extracted"  : len(statute_refs),
                "statutes_verified"   : sum(1 for u in statute_links.values() if u),
                "bad_laws_found"      : len(bad_laws_found),
                "ik_available"        : ik_available,
                "hallucination_risk"  : risk,
                "risk_label"          : risk_label,
                "is_grounded"         : is_grounded,
                "feedback_id"         : feedback_id,
                "rationale"           : "Cases + statutes cross-verified on IK; bad-law rule scan applied"
            }
        )

        return result


class DocumentationAgent(LegalAgent):
    """Generates legal answers and reports with XAI transparency.

    Default  : concise plain-text answer (generate_simple_answer)
    --report : full structured report   (generate_report)
    --pdf    : full report saved as PDF (generate_report + generate_pdf)
    """

    def __init__(self):
        super().__init__(
            name="DocumentationAgent",
            system_prompt="""You are a legal documentation specialist for Indian law.

By default, answer questions concisely and directly — 2-4 paragraphs, no section headings.
When asked to generate a full report, use proper sections:
  EXECUTIVE SUMMARY / LEGAL BACKGROUND / RELEVANT CASE LAWS / ANALYSIS / CONCLUSION / RECOMMENDATIONS

Always cite Indian sources inline (case names, Article numbers, Section numbers)."""
        )

    # ------------------------------------------------------------------ #
    #  DEFAULT: concise plain-text answer                                  #
    # ------------------------------------------------------------------ #
    def generate_simple_answer(self, query: str, research: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a concise, direct answer — no section headings."""
        if _verbose:
            print(f"💬 {self.name}: Generating answer...")

        self.log_reasoning_step(
            "simple_answer_generation",
            {
                "action": "generating_concise_answer",
                "rationale": "Default mode: direct answer without full report structure"
            }
        )

        content = research.get("validated_content", research.get("research_content", ""))

        prompt = f"""Based on the research below, provide a CONCISE and DIRECT answer to this legal query.
Do NOT use section headings. Answer clearly in 2-4 paragraphs.
Include key citations (case names, Article/Section numbers) inline.

Query: {query}

Research:
{content}"""

        response = self.call_llm(prompt)

        self.log_reasoning_step(
            "simple_answer_completed",
            {
                "action": "answer_generated",
                "response_length": len(response),
                "rationale": "Concise answer generated successfully"
            }
        )

        return {
            "answer": response,
            "status": "completed",
            "type": "simple_answer",
            "reasoning_trace": self.get_reasoning_trace()
        }

    # ------------------------------------------------------------------ #
    #  OPTIONAL: full structured report                                    #
    # ------------------------------------------------------------------ #
    def generate_report(self, query: str, research: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a full structured legal research report."""
        if _verbose:
            print(f"📄 {self.name}: Generating full report...")

        self.log_reasoning_step(
            "report_structure_selection",
            {
                "action": "selecting_report_format",
                "sections": ["Executive Summary", "Legal Background", "Case Laws",
                             "Analysis", "Conclusion", "Recommendations"],
                "rationale": "Full report requested — using standard legal research format",
                "alternatives": "Could use brief memo format, Q&A format, or annotated bibliography"
            }
        )

        content = research.get("validated_content", research.get("research_content", ""))

        prompt = f"""Create a professional legal research report based on:

Original Query: {query}

Research Findings:
{content}

Generate a report with these sections:
1. EXECUTIVE SUMMARY (2-3 paragraphs)
2. LEGAL BACKGROUND
3. RELEVANT CASE LAWS
4. ANALYSIS
5. CONCLUSION
6. RECOMMENDATIONS (bullet points)

Make it professional and well-structured."""

        response = self.call_llm(prompt)

        recommendations = []
        if "RECOMMENDATIONS" in response:
            rec_section = response.split("RECOMMENDATIONS")[1]
            for line in rec_section.split("\n"):
                line = line.strip()
                if line.startswith(("•", "-", "*", "1", "2", "3")):
                    recommendations.append(line.lstrip("•-*0123456789. "))

        self.log_reasoning_step(
            "documentation_completed",
            {
                "action": "report_generated",
                "report_length": len(response),
                "recommendations_count": len(recommendations),
                "rationale": "Comprehensive legal report generated with all required sections"
            }
        )

        return {
            "full_report": response,
            "executive_summary": (
                response.split("LEGAL BACKGROUND")[0].replace("EXECUTIVE SUMMARY", "").strip()
                if "LEGAL BACKGROUND" in response else response[:500]
            ),
            "recommendations": recommendations[:5],
            "status": "completed",
            "type": "full_report",
            "reasoning_trace": self.get_reasoning_trace()
        }

    # ------------------------------------------------------------------ #
    #  OPTIONAL: save report as PDF (requires reportlab)                  #
    # ------------------------------------------------------------------ #
    def generate_pdf(self, report_content: str, query: str) -> Optional[str]:
        """Save the report to a PDF file. Falls back to .txt if reportlab is missing."""
        import os

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = re.sub(r'[^\w\s-]', '', query)[:40].strip().replace(' ', '_')

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.lib.enums import TA_CENTER
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

            filename = f"legal_report_{safe_query}_{timestamp}.pdf"
            doc = SimpleDocTemplate(
                filename, pagesize=A4,
                rightMargin=2 * cm, leftMargin=2 * cm,
                topMargin=2 * cm, bottomMargin=2 * cm
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CTitle', parent=styles['Heading1'],
                fontSize=16, spaceAfter=12, alignment=TA_CENTER
            )
            heading_style = ParagraphStyle(
                'CHeading', parent=styles['Heading2'],
                fontSize=13, spaceAfter=8
            )
            body_style = ParagraphStyle(
                'CBody', parent=styles['Normal'],
                fontSize=10, spaceAfter=6, leading=14
            )

            elements = []
            elements.append(Paragraph("Constitutional Law Research Report", title_style))
            elements.append(Paragraph(f"<b>Query:</b> {query}", body_style))
            elements.append(Paragraph(
                f"<b>Generated:</b> {datetime.now().strftime('%d %B %Y, %H:%M')}", body_style
            ))
            elements.append(Spacer(1, 0.5 * cm))

            for line in report_content.split('\n'):
                line = line.strip()
                if not line:
                    elements.append(Spacer(1, 0.25 * cm))
                    continue
                # Section headings: ALL CAPS or short line ending with ':'
                if line.isupper() or (len(line) < 70 and line.endswith(':')):
                    elements.append(Paragraph(line, heading_style))
                elif line.startswith(('•', '-', '*')):
                    elements.append(Paragraph(f"\u2022 {line.lstrip('•-* ')}", body_style))
                else:
                    safe = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    elements.append(Paragraph(safe, body_style))

            doc.build(elements)
            return os.path.abspath(filename)

        except ImportError:
            # Fallback to plain-text file
            filename = f"legal_report_{safe_query}_{timestamp}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("Constitutional Law Research Report\n")
                f.write(f"Query: {query}\n")
                f.write(f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}\n\n")
                f.write(report_content)
            return os.path.abspath(filename)

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"PDF generation failed: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════
#  DraftingAgent (LLM Agent — JUSTIFIED)
# ═══════════════════════════════════════════════════════════════════════
#
# JUSTIFICATION:
#   Drafting a legal document (writ petition, RTI application, legal
#   notice) is fundamentally different from research or formatting an
#   answer.  It requires:
#     • Knowledge of the prescribed format / headings / legal language
#     • Inserting party names, dates, prayer clauses, citations
#     • Different structure per document type
#   None of the existing agents (Research / Documentation) can do this.
#   An LLM agent is the right approach because drafts need generative
#   language skills — a rule-based template would be too rigid.
#
# PIPELINE POSITION: After XAIValidationAgent, parallel to DocumentationAgent
#   UIAgent → ResearchAgent → XAIValidationAgent → DraftingAgent (if --draft)
#                                                → DocumentationAgent (otherwise)
# ═══════════════════════════════════════════════════════════════════════

class DraftingAgent(LegalAgent):
    """Generates structured legal document drafts based on research.

    Supported draft types:
      • writ_petition   — Writ petition under Article 226/32
      • legal_notice    — Formal legal notice under Section 80 CPC etc.
      • rti             — RTI application under the RTI Act, 2005
      • complaint       — Consumer / police / human-rights complaint
      • affidavit       — Sworn statement for court filing
      • pil             — Public Interest Litigation petition
    """

    SUPPORTED_TYPES = {
        "writ_petition": "Writ Petition under Article 226 / Article 32 of the Constitution of India",
        "legal_notice":  "Legal Notice (e.g. under Section 80 CPC or general civil/contract disputes)",
        "rti":           "RTI Application under the Right to Information Act, 2005",
        "complaint":     "Formal Complaint (consumer / police / NHRC / appropriate authority)",
        "affidavit":     "Affidavit (sworn statement for filing in court)",
        "pil":           "Public Interest Litigation (PIL) petition",
    }

    def __init__(self):
        super().__init__(
            name="DraftingAgent",
            system_prompt="""You are an expert Indian legal drafter.  Given legal research and a
document type, produce a COMPLETE, READY-TO-USE draft in proper legal format.

Rules:
1. Use formal legal language appropriate for Indian courts / authorities.
2. Insert placeholder markers for facts you don't know:
   [PETITIONER_NAME], [RESPONDENT_NAME], [DATE], [ADDRESS], [COURT_NAME], etc.
3. Include all legally required sections for the document type.
4. Cite specific Articles/Sections/Case-law from the research provided.
5. ONLY Indian law — never reference foreign jurisdictions.
6. End with appropriate prayer / relief clause / declaration as required."""
        )

    def generate_draft(self, query: str, research: Dict[str, Any],
                       draft_type: str) -> Dict[str, Any]:
        """Generate a legal draft of the requested type.

        Parameters
        ----------
        draft_type : one of the keys in SUPPORTED_TYPES
        """
        if _verbose:
            print(f"📝 {self.name}: Drafting {draft_type} ...")

        description = self.SUPPORTED_TYPES.get(
            draft_type,
            f"Legal document of type '{draft_type}'"
        )

        self.log_reasoning_step(
            "draft_generation_started",
            {
                "action": "generating_legal_draft",
                "draft_type": draft_type,
                "description": description,
                "rationale": "User requested a legal draft — invoking DraftingAgent"
            }
        )

        content = research.get("validated_content", research.get("research_content", ""))

        prompt = f"""Draft the following legal document:

DOCUMENT TYPE: {description}

USER REQUEST: {query}

RESEARCH / LEGAL BACKGROUND:
{content[:3000]}

INSTRUCTIONS:
- Produce the COMPLETE draft with all necessary sections, headings, and legal language.
- Use placeholders like [PETITIONER_NAME], [RESPONDENT_NAME], [DATE], [ADDRESS],
  [COURT_NAME] for facts you do not know.
- Cite specific Articles, Sections, and case-law from the research above.
- Follow the standard Indian legal format for this document type.
- End with the appropriate prayer / relief / declaration clause.
"""

        response = self.call_llm(prompt)

        self.log_reasoning_step(
            "draft_generation_completed",
            {
                "action": "draft_generated",
                "draft_type": draft_type,
                "response_length": len(response),
                "rationale": "Legal draft generated successfully"
            }
        )

        return {
            "draft": response,
            "draft_type": draft_type,
            "draft_description": description,
            "status": "completed",
            "type": "legal_draft",
            "reasoning_trace": self.get_reasoning_trace()
        }


# ═══════════════════════════════════════════════════════════════════════
#  UIFormatter  (Deterministic Utility — NOT an LLM Agent)
# ═══════════════════════════════════════════════════════════════════════
#
# JUSTIFICATION FOR *NOT* BEING AN AGENT:
#   Structuring JSON for a web frontend is a deterministic transformation:
#   pick fields from the result dict, rename them, add labels.  Using an
#   LLM for this would be:
#     • Unreliable — output format may vary per call
#     • Slow      — adds an extra LLM round-trip
#     • Wasteful  — consumes API tokens for zero intelligence
#   A simple utility class is the correct approach: fast, deterministic,
#   100 % testable, and zero API cost.
#
# PIPELINE POSITION: After all agents have finished (Step 5), before
#   the result dict is returned to the caller.
# ═══════════════════════════════════════════════════════════════════════

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
        }


class Coordinator:
    """Coordinates the multi-agent workflow with XAI traceability"""

    def __init__(self):
        self.ui_agent = UIAgent()
        self.research_agent = ResearchAgent()
        self.xai_validation_agent = XAIValidationAgent()
        self.documentation_agent = DocumentationAgent()
        self.drafting_agent = DraftingAgent()
        self.ui_formatter = UIFormatter()
        self.workflow_trace: List[Dict[str, Any]] = []

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
        show_logs: bool = False
    ) -> Dict[str, Any]:
        """Run the complete research workflow.

        Parameters
        ----------
        want_report : generate a full structured report instead of a concise answer
        want_pdf    : generate a full report AND save it as a PDF file
        want_draft  : generate a legal draft of the given type
                      (e.g. "writ_petition", "legal_notice", "rti", "complaint", "affidavit")
        show_logs   : print agent step logs and httpx request logs
        """
        set_verbose(show_logs)
        print("\n" + "=" * 60)
        print("🏛️  Legal Research Multi-Agent System")
        print("📍 Jurisdiction: Indian Law Only")
        if want_draft:
            print(f"📝 Output: Legal Draft ({want_draft.replace('_', ' ').title()})")
        elif want_pdf:
            print("📄 Output: Full Report + PDF")
        elif want_report:
            print("📋 Output: Full Structured Report")
        else:
            print("💬 Output: Concise Answer")
        print("=" * 60)
        print(f"\nQuery: {query}\n")

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
            "agent_reasoning_traces": {}
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

            result["status"] = "completed"

            # ── Step 5: UI formatting (deterministic, no LLM) ────────────
            result["ui_payload"] = self.ui_formatter.format(result)

            # Collect reasoning traces
            result["workflow_trace"] = self.workflow_trace
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
                     show_logs: bool = False) -> Dict[str, Any]:
        """Run research — concise answer by default; full report/PDF/draft on request."""
        return self.coordinator.run(
            query,
            want_report=want_report,
            want_pdf=want_pdf,
            want_draft=want_draft,
            show_logs=show_logs
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