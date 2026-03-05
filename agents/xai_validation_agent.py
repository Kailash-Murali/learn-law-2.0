"""XAIValidationAgent - Enforces anti-hallucination measures through cross-verification.

This agent validates legal research via Indian Kanoon API cross-verification,
extracting citations, checking for repealed laws, and computing hallucination risk.
"""

import json
import re
import uuid
import requests
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .base_agent import LegalAgent, _remove_markdown_formatting
from config import Config

_logger = logging.getLogger(__name__)


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
    # Keys are REGEX PATTERNS (not simple substrings) with word boundaries to avoid false positives.
    # EVALUATION: Rule-based is unambiguously correct for most critical laws.
    # Only include laws that are DEFINITELY repealed or struck down.
    REPEALED_OR_BAD_LAWS: Dict[str, tuple] = {
        # Most critical and unambiguous bad laws
        r'\bsection\s+66a(?:\s+|$)': (
            "Section 66A of the IT Act, 2000",
            "Struck down as unconstitutional — Shreya Singhal v. Union of India (2015)",
        ),
        r'\bsection\s+124a(?:\s+ipc)?(?:\s+|$)': (
            "Section 124A IPC — Sedition",
            "SC stayed all prosecutions in 2022 (S.G. Vombatkere v. UoI); under constitutional review",
        ),
    }
    
    # DEPRECATED: Removed overly aggressive patterns that caused false positives:
    # - "tada", "pota" — too short, match in unrelated contexts
    # - "section 377 ipc" — partially struck down (affects consenting adults only), not fully repealed
    # - "imdt act" — less commonly cited, risk of false positives
    # - "prevention of terrorism ordinance" — too vague

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

    def _analyze_verified_cases_for_bad_laws(
        self,
        verified_cases: List[str],
        citation_links: Dict[str, Optional[str]],
        original_query: str
    ) -> List[Dict[str, Any]]:
        """
        Phase 2: Analyze verified Indian case law to extract constitutional defect claims.
        
        For each verified case, uses LLM to identify laws that are claimed to be:
        - Struck down (completely or partially)
        - Stayed (enforcement halted)
        - Under constitutional review
        - Narrowly interpreted
        
        Only reports findings grounded in judicial holdings, not dicta.
        
        Args:
            verified_cases: List of case names verified to exist on Indian Kanoon
            citation_links: Dict mapping case names to Indian Kanoon URLs
            original_query: The original user research query for context
            
        Returns:
            List of bad laws found with case references and holdings
        """
        if not verified_cases:
            return []
        
        # Cap analysis at 8 cases to optimize LLM context
        cases_to_analyze = verified_cases[:8]
        
        # Format verified cases as JSON for LLM prompt
        cases_json = json.dumps({
            "cases": [
                {
                    "name": case,
                    "ik_url": citation_links.get(case, "")
                }
                for case in cases_to_analyze
            ],
            "count": len(cases_to_analyze),
            "original_query": original_query
        }, indent=2)
        
        # Construct specialized prompt for bad law analysis
        analysis_prompt = f"""You are a Constitutional Law Bad-Law Detection Specialist. Your exclusive task is to analyze verified Indian case law to identify constitutional defects.

VERIFIED CASES TO ANALYZE:
{cases_json}

TASK: For EACH case, extract any claims that specific laws are unconstitutional, struck down, partially invalid, stayed, or otherwise legally defective.

ANALYSIS REQUIREMENTS:
1. Laws explicitly claimed to be unconstitutional / struck down / invalid / stayed
2. The specific provision(s) affected (e.g., "entire section" vs. "as applied to X")
3. The judicial holding or ratio decidendi supporting the claim
4. The status category: struck_down_completely | struck_down_partially | stayed_enforcement | under_constitutional_review | narrowly_interpreted

CRITICAL FILTERS:
- HOLDING-ONLY: Report ONLY if law invalidity is the core holding or ratio decidendi
- EXCLUDE: Incidental mentions in dicta, hypothetical discussions, or commentary
- SPECIFICITY: If partiality ("struck down as applied to X"), explicitly state the scope
- YEAR: Include year for temporal validation
- JUDGES: List presiding judges if available

DECISION QUALITY INDICATORS:
- Single-judge dissent with good reasoning = lower weight ("discussion_only": true)
- Multi-judge bench consensus = full weight
- Constitutional bench (5+ judges) = highest weight
- Recent years (2015+) = more current

OUTPUT FORMAT (STRICT JSON ONLY - no markdown, no explanation):

[
  {{
    "case_name": "Case Name v. Respondent (Year)",
    "bench_size": <number>,
    "bad_laws_identified": [
      {{
        "law": "Full legal citation of the provision",
        "status": "struck_down_completely|struck_down_partially|stayed_enforcement|under_review|narrowly_interpreted",
        "scope": "Description of what is invalid",
        "holding": "1-2 sentence judicial holding about invalidity",
        "ratio_decidendi": "The binding principle/reasoning",
        "discussion_only": false,
        "impact_description": "Practical impact of this invalidity",
        "judges": "List of key judges"
      }}
    ],
    "confidence_level": "high|medium|low"
  }}
]

If NO bad laws found, return:
[
  {{
    "case_name": "Case Name (Year)",
    "bad_laws_identified": [],
    "confidence_level": "high"
  }}
]

CONFIDENTIALITY NOTES:
- If uncertain about a claim, DO NOT REPORT IT
- If only incidental mention, use "discussion_only": true
- Mark confidence as "low" if reasoning is unclear
- Better to miss a bad law than falsely report one"""

        self.log_reasoning_step(
            "bad_law_analysis_initiated",
            {
                "action": "analyzing_verified_cases_for_constitutional_defects",
                "verified_cases_count": len(cases_to_analyze),
                "rationale": "Extract constitutional defect claims from cited case holdings"
            }
        )
        
        # Call LLM for bad law analysis
        try:
            response = self.call_llm(analysis_prompt, log_reasoning=False)
            
            # Parse JSON response
            bad_laws_by_case = self._parse_bad_law_analysis_response(response)
            
            self.log_reasoning_step(
                "bad_law_analysis_completed",
                {
                    "action": "ik_cross_verification_of_constitutional_defects",
                    "total_bad_laws_identified": sum(
                        len(case_data.get("bad_laws_identified", []))
                        for case_data in bad_laws_by_case
                    ),
                    "cases_analyzed": len(cases_to_analyze)
                }
            )
            
            # Flatten and standardize bad laws for integration
            bad_laws_found = self._flatten_bad_law_findings(bad_laws_by_case)
            
            return bad_laws_found
            
        except Exception as e:
            _logger.warning(f"Bad law analysis failed: {e}")
            self.log_reasoning_step(
                "bad_law_analysis_error",
                {
                    "action": "bad_law_analysis_failed",
                    "error": str(e),
                    "fallback": "skipping dynamic bad law analysis"
                }
            )
            return []

    def _parse_bad_law_analysis_response(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response for bad law analysis.
        
        Extracts JSON array from response and validates structure.
        Handles trailing whitespace and extraneous text after JSON.
        """
        try:
            # Try to find JSON array in response
            bracket_start = response.index("[")
            bracket_end = response.rindex("]") + 1
            json_str = response[bracket_start:bracket_end].strip()
            
            # Attempt to parse JSON
            parsed = json.loads(json_str)
            
            if not isinstance(parsed, list):
                _logger.warning(f"Bad law analysis response is not a list: {type(parsed)}")
                return []
            
            return parsed
            
        except json.JSONDecodeError as e:
            # If standard parsing fails, try incremental approach
            # Start from "[" and scan forward to find valid JSON endpoint
            try:
                bracket_start = response.index("[")
                # Try parsing progressively longer substrings from the start
                for i in range(len(response), bracket_start, -1):
                    candidate = response[bracket_start:i].strip()
                    if not candidate.endswith("]"):
                        continue
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, list):
                            _logger.debug(f"Successfully parsed bad law response with incremental approach at position {i}")
                            return parsed
                    except json.JSONDecodeError:
                        continue
                
                _logger.warning(f"Failed to parse bad law analysis JSON (incremental approach exhausted): {e}")
                return []
                
            except (ValueError, json.JSONDecodeError) as inner_e:
                _logger.warning(f"Failed to parse bad law analysis JSON (both methods): {inner_e}")
                return []
        except (ValueError, IndexError) as e:
            _logger.warning(f"Failed to locate JSON array in bad law response: {e}")
            return []

    def _flatten_bad_law_findings(self, bad_laws_by_case: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Flatten bad law findings from case-structured format to flat list.
        
        Deduplicates laws appearing in multiple cases and normalizes structure.
        """
        seen_laws = {}  # Track laws by normalized name
        flattened = []
        
        for case_entry in bad_laws_by_case:
            case_name = case_entry.get("case_name", "Unknown")
            bad_laws = case_entry.get("bad_laws_identified", [])
            
            for bad_law in bad_laws:
                law_name = bad_law.get("law", "").strip()
                if not law_name:
                    continue
                
                # Normalize law name (lowercase for comparison)
                normalized = law_name.lower()
                
                # If we've seen this law before, merge the findings
                if normalized in seen_laws:
                    # Keep the one with higher confidence
                    existing = seen_laws[normalized]
                    if bad_law.get("confidence_level") == "high" and existing.get("confidence_level") != "high":
                        seen_laws[normalized] = self._standardize_bad_law(bad_law, case_name)
                else:
                    # New law finding
                    standardized = self._standardize_bad_law(bad_law, case_name)
                    seen_laws[normalized] = standardized
                    flattened.append(standardized)
        
        return flattened

    def _standardize_bad_law(self, bad_law: Dict[str, Any], case_name: str) -> Dict[str, Any]:
        """
        Standardize bad law finding to consistent structure for validation output.
        """
        return {
            "law": bad_law.get("law", ""),
            "reason": bad_law.get("holding", bad_law.get("reason", "")),
            "case": case_name,
            "status": bad_law.get("status", "struck_down_completely"),
            "scope": bad_law.get("scope", ""),
            "year": bad_law.get("year", None),
            "confidence": bad_law.get("confidence_level", "medium"),
            "discussion_only": bad_law.get("discussion_only", False)
        }

    def validate(self, query: str, research: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate research via Indian Kanoon API cross-verification.

        Steps:
          1. Regex extracts Article/Section refs (always reliable).
          2. Regex extracts statute/act citations.
          3. LLM extracts case names; each is looked up on Indian Kanoon.
          4. Statutes are looked up on Indian Kanoon.
          5. (NEW - Phase 2) LLM analyzes verified case law for constitutional defects.
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

        # ── Step 1c: Bad-law scan → DELEGATED TO PHASE 2 ──────────────────────
        # Phase 2 (dynamic analysis) replaces static regex-based detection.
        # Bad laws will be detected from verified case law (Step 3c).
        bad_laws_found: List[Dict[str, Any]] = []

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

        # ── Step 3c (NEW - PHASE 2): Dynamic bad law analysis from verified cases ──
        # Analyze verified case law to identify constitutional defects dynamically
        if ik_available and verified:
            bad_laws_found = self._analyze_verified_cases_for_bad_laws(
                verified_cases=verified,
                citation_links=citation_links,
                original_query=query
            )
        else:
            if not ik_available:
                self.log_reasoning_step(
                    "bad_law_analysis_skipped",
                    {
                        "reason": "IK_API_TOKEN not set",
                        "action": "skipping_dynamic_bad_law_analysis"
                    }
                )
            if not verified:
                self.log_reasoning_step(
                    "bad_law_analysis_skipped",
                    {
                        "reason": "No verified cases",
                        "action": "skipping_dynamic_bad_law_analysis"
                    }
                )

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

        # 4c — bad-law penalty (Phase 2: dynamic analysis, weighted by confidence)
        for bl in bad_laws_found:
            # Skip penalties for incidental mentions (discussion_only)
            if bl.get("discussion_only", False):
                continue
            
            # Weight by confidence level
            confidence = bl.get("confidence", "medium")
            if confidence == "high":
                risk_increment = 0.15
            elif confidence == "medium":
                risk_increment = 0.10
            else:  # low
                risk_increment = 0.05
            
            risk = min(1.0, risk + risk_increment)
            law_name = bl.get("law", "Unknown Law")
            case_citation = bl.get("case", "")
            status = bl.get("status", "struck_down_completely")
            flags.append(f"BAD LAW IDENTIFIED: {law_name} ({status}) — {case_citation}")

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
                "action"              : "ik_cross_verification_done_with_phase2_bad_law_analysis",
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
                "rationale"           : "Cases + statutes cross-verified on IK; Phase 2 dynamic bad-law analysis applied to verified cases"
            }
        )

        return result
