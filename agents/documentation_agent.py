"""DocumentationAgent - Generates legal answers and reports with XAI transparency.

Supports three output modes:
- concise plain-text answer (default)
- full structured report with sections
- PDF export of reports
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .base_agent import LegalAgent, _remove_markdown_formatting, _verbose
from config import Config

_logger = logging.getLogger(__name__)


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

IMPORTANT: Do NOT use markdown formatting (**bold**, *italic*, ##headings##, etc). Use plain text only.

Query: {query}

Research:
{content}"""

        response = self.call_llm(prompt)

        # Remove markdown formatting from response
        response = _remove_markdown_formatting(response)

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

IMPORTANT: Do NOT use markdown formatting (**bold**, *italic*, etc). Use plain text only.
Make it professional and well-structured."""

        response = self.call_llm(prompt)

        # Remove markdown formatting from response
        response = _remove_markdown_formatting(response)

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
            _logger.error(f"PDF generation failed: {e}")
            return None

    # ------------------------------------------------------------------ #
    #  Contrastive / Counterfactual XAI analysis                          #
    # ------------------------------------------------------------------ #
    def generate_counterfactuals(self, query: str, research_summary) -> dict:
        """Generate contrastive and counterfactual analysis for XAI transparency."""
        if not isinstance(research_summary, str):
            research_summary = str(research_summary)
        prompt = (
            "Analyse this legal query contrastively and counterfactually.\n\n"
            f"Query: {query}\n"
            f"Research context: {research_summary[:1500]}\n\n"
            "Return a JSON object with exactly these keys:\n"
            '- "contrastive_points": list of 2-3 strings explaining what distinguishes '
            "this legal position from common alternative positions\n"
            '- "counterfactuals": list of 2-3 strings, each starting with '
            '"If [condition] were different, [outcome] would change because [reason]"\n'
            '- "key_distinctions": list of 2-3 strings identifying the key legal factors '
            "that determine the outcome\n\n"
            "Return JSON only — no markdown fences, no other text."
        )
        try:
            response = self.call_llm(prompt)
            clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", response.strip(), flags=re.DOTALL)
            parsed = json.loads(clean)
            return {
                "contrastive_points": [str(p) for p in parsed.get("contrastive_points", [])],
                "counterfactuals": [str(c) for c in parsed.get("counterfactuals", [])],
                "key_distinctions": [str(d) for d in parsed.get("key_distinctions", [])],
            }
        except Exception as exc:
            _logger.warning("Counterfactual generation failed: %s", exc)
            return {"contrastive_points": [], "counterfactuals": [], "key_distinctions": []}
