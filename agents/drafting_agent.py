"""DraftingAgent - Generates structured legal document drafts based on research.

Supports writ petitions, legal notices, RTI applications, complaints, affidavits, and PILs.
"""

import logging
from typing import Dict, List, Any

from .base_agent import LegalAgent, _remove_markdown_formatting, _verbose
from config import Config

_logger = logging.getLogger(__name__)


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
- Do NOT use markdown formatting (**bold**, *italic*, etc). Use plain text only.
"""

        response = self.call_llm(prompt)

        # Remove markdown formatting from response
        response = _remove_markdown_formatting(response)

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
