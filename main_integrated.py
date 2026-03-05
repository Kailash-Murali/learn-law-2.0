"""
Constitutional Law Research System - Integrated Main Entry Point
Uses AutoGen multi-agent system with XAIValidationAgent for anti-hallucination.
"""

import argparse
import json
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConstitutionalLawCLI:
    """Command-line interface for Constitutional Law Research."""

    def __init__(self, show_logs: bool = False):
        self.show_logs = show_logs
        self.research_system = None
        # Track queries by feedback_id so feedback can be stored with context
        self._query_by_fid: dict[str, str] = {}

    def initialize(self):
        """Initialize the AutoGen research system."""
        try:
            from autogen_agent import AutoGenLegalResearch
            self.research_system = AutoGenLegalResearch()
            return True
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            print(f"[Error] Failed to initialize: {e}")
            return False

    def _parse_inline_flags(self, raw_query: str):
        """
        Detect trailing inline flags in a query string.
        Supported flags: --pdf, --report, --logs, --draft <type>, --research, --draft <type>
        Returns (clean_query, want_report, want_pdf, want_draft, show_logs_override, want_research)
        """
        want_pdf = False
        want_report = False
        want_research = False
        want_draft: str | None = None
        show_logs_override = False

        # Draft type aliases for convenience
        _DRAFT_ALIASES = {
            "writ": "writ_petition", "petition": "writ_petition",
            "notice": "legal_notice", "legal_notice": "legal_notice",
            "rti": "rti",
            "complaint": "complaint",
            "affidavit": "affidavit",
            "pil": "pil",
        }

        tokens = raw_query.strip().split()
        remaining = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok == "--pdf":
                want_pdf = True
            elif tok == "--report":
                want_report = True
            elif tok == "--research":
                want_research = True
            elif tok == "--logs":
                show_logs_override = True
            elif tok == "--draft":
                # Next token is the draft type (optional, defaults to writ_petition)
                if i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                    i += 1
                    want_draft = _DRAFT_ALIASES.get(tokens[i].lower(), tokens[i].lower())
                else:
                    want_draft = "writ_petition"
            else:
                remaining.append(tok)
            i += 1

        clean_query = " ".join(remaining)
        return clean_query, want_report, want_pdf, want_draft, show_logs_override, want_research

    def process_query(self, query: str, want_report: bool = False,
                      want_pdf: bool = False, want_draft: str | None = None,
                      show_logs: bool = False, want_research: bool = False) -> dict:
        """Process a legal research query."""

        try:
            result = self.research_system.run_research(
                query, want_report=want_report, want_pdf=want_pdf,
                want_draft=want_draft, show_logs=show_logs, want_research=want_research
            )
            return result
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            return {"error": str(e), "status": "failed"}

    def display_result(self, result: dict, show_logs: bool = False):
        """Display the research result."""
        if result.get("error") and result.get("status") != "rejected":
            print(f"\n[Error] {result['error']}")
            return

        # ── Jurisdiction rejection ───────────────────────────────────────
        if result.get("status") == "rejected":
            print("\n" + "="*70)
            print("❌ REQUEST REJECTED")
            print("="*70)
            print(f"\n{result.get('error', 'Request rejected')}")
            if result.get("parsed_query", {}).get("detected_jurisdiction"):
                print(f"\nDetected jurisdiction: {result['parsed_query']['detected_jurisdiction']}")
            print("\nThis system only supports Indian legal jurisdiction.")
            print("Please ask questions about Indian constitutional law, case laws, or statutes.")
            return

        print("\n" + "="*70)

        doc = result.get("documentation", {})
        doc_type = doc.get("type", "simple_answer")

        # ── Simple answer (default) ──────────────────────────────────────
        if doc_type == "simple_answer":
            print("\n" + doc.get("answer", "No answer generated."))
        # ── Legal draft ─────────────────────────────────────────────────────
        elif doc_type == "legal_draft":
            # print("📝 LEGAL DRAFT")
            # print(f"   Type: {doc.get('draft_description', doc.get('draft_type', 'N/A'))}")
            # print("="*70)
            print("\n" + doc.get("draft", "No draft generated."))
        # ── Full structured report ───────────────────────────────────────
        else:
            print("📄 LEGAL RESEARCH REPORT")
            print("="*70)
            full_report = doc.get("full_report", "")
            if full_report:
                print("\n" + full_report)
            else:
                print("\n📋 EXECUTIVE SUMMARY:\n")
                print(doc.get("executive_summary", "N/A"))
                print("\n📌 RECOMMENDATIONS:")
                for rec in doc.get("recommendations", []):
                    print(f"  • {rec}")

        # ── PDF path ─────────────────────────────────────────────────────
        if result.get("pdf_path"):
            print("\n" + "-"*70)
            print(f"📎 PDF saved to: {result['pdf_path']}")

        # ── Validation summary (always shown) ────────────────────────────
        validation = result.get("validation", {})
        if validation:
            risk       = validation.get("hallucination_risk", 0)
            risk_label = "LOW ✅" if risk < 0.35 else "MEDIUM ⚠️" if risk < 0.65 else "HIGH ❌"
            flags      = validation.get("flags", [])
            feedback_id = validation.get("feedback_id", "N/A")
            citation_links  = validation.get("citation_links", {})
            article_refs    = validation.get("article_refs", [])
            verified        = validation.get("verified_on_ik", [])
            unverified      = validation.get("unverified_on_ik", [])
            ik_available    = validation.get("ik_available", False)
            print(f"\n  Factual grounding : {'✅ Grounded' if validation.get('is_grounded') else '⚠️  Weak grounding'}")
            print(f"  Hallucination risk: {risk_label} ({risk:.0%})")
            print(f"  IK verification   : {'✅ Active' if ik_available else '⚠️  Skipped (IK_API_TOKEN not set)'}")

            # ── Bad-law warnings (most prominent — shown first) ─────────────
            bad_laws = validation.get("bad_laws_found", [])
            if bad_laws:
                print(f"\n  ❌ BAD LAWS DETECTED (rule-based check):")
                for bl in bad_laws:
                    print(f"    ✗ {bl['law']}")
                    print(f"      {bl['reason']}")

            # ── Case citations ──────────────────────────────────────────────
            if citation_links:
                total_cases = len(citation_links)
                print(f"\n  Case Citations ({len(verified)}/{total_cases} verified on Indian Kanoon):")
                for case, url in list(citation_links.items())[:8]:
                    if url:
                        print(f"    ✅ {case}")
                        print(f"       {url}")
                    else:
                        print(f"    ⚠️  {case}  (not found on Indian Kanoon)")

            # ── Statute citations ───────────────────────────────────────────
            statute_links = validation.get("statute_links", {})
            statute_refs  = validation.get("statute_refs", [])
            if statute_links:
                n_verified = sum(1 for u in statute_links.values() if u)
                print(f"\n  Statute Citations ({n_verified}/{len(statute_links)} verified on Indian Kanoon):")
                for statute, url in list(statute_links.items())[:6]:
                    if url:
                        print(f"    ✅ {statute}")
                        print(f"        {url}")
                    else:
                        print(f"    ⚠️  {statute}  (not found on Indian Kanoon)")
            elif not statute_refs and not article_refs:
                print(f"\n  Statutes: ⚠️  No statute citations found in response")

            if article_refs:
                print(f"\n  Constitutional Refs: {', '.join(article_refs[:6])}")

            # if flags:
            #     print(f"\n  Flags:")
            #     for f in flags[:5]:
            #         print(f"    {f}")

        # ── Springer Research Papers (if --research was used) ────────────
        springer_results = result.get("springer_results", {})
        if springer_results:
            papers = springer_results.get("combined_papers", [])
            status = springer_results.get("status", "unknown")
            total = springer_results.get("total_papers", 0)
            
            if papers and total > 0:
                print(f"\n  Springer Academic Research ({total} papers found):")
                for paper in papers[:10]:
                    title = paper.get("title", "N/A")
                    url = paper.get("url", "")
                    authors = paper.get("authors", "")
                    journal = paper.get("journal", "")
                    doi = paper.get("doi", "")
                    source = paper.get("source", "Springer")
                    
                    print(f"\n    📄 {title}")
                    if authors:
                        print(f"       Authors: {authors[:100]}")
                    if journal:
                        print(f"       Journal: {journal}")
                    if doi:
                        print(f"       DOI: {doi}")
                    if url:
                        print(f"       🔗 {url}")
                        print(f"       Source: {source}")
                    else:
                        print(f"       ⚠️  No direct link available")
            elif status == "failed":
                errors = springer_results.get("errors", [])
                if errors:
                    print(f"\n  Springer Research: ⚠️  {errors[0]}")
                else:
                    print(f"\n  Springer Research: ⚠️  Search failed")
            elif status == "no_results":
                print(f"\n  Springer Research: ℹ️  No papers found matching your query")
            else:
                print(f"\n  Springer Research: ℹ️  Search status: {status}")
            
            print(f"\n  Feedback ID       : {feedback_id}")
            print(f"  (Type 'feedback {feedback_id} <your issue>' to report a problem)")

        # ── Agent logs (only when requested) ────────────────────────────
        if show_logs and result.get("agent_reasoning_traces"):
            print("\n" + "="*70)
            print("📊 AGENT LOGS")
            print("="*70)
            for agent, trace in result["agent_reasoning_traces"].items():
                print(f"\n── {agent} ({len(trace)} steps) ──")
                for step in trace:
                    ts = step.get("timestamp", "")[-8:]
                    action = step.get("details", {}).get("action", "N/A")
                    rationale = step.get("details", {}).get("rationale", "")
                    print(f"  [{ts}] {step.get('step', 'N/A')}: {action}")
                    if rationale:
                        print(f"         rationale: {rationale[:80]}")

    def interactive_mode(self):
        """Run interactive query mode."""
        print("\n" + "="*60)
        print("Aram")
        print("="*60)
        if self.show_logs:
            print("Logs: ENABLED (global)")
        print("\nCommands: 'quit' to exit, 'help' for info")
        print("Inline flags: append --report, --pdf, --draft, --research, --logs to any query")
        print("-"*60)

        while True:
            try:
                raw = input("\nEnter your legal query: ").strip()

                if not raw:
                    continue
                elif raw.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye!")
                    break
                elif raw.lower() == 'help':
                    self.show_help()
                    continue
                elif raw.lower().startswith("feedback"):
                    self._handle_feedback(raw)
                    continue

                # Parse inline flags
                query, want_report, want_pdf, want_draft, logs_override, want_research = self._parse_inline_flags(raw)
                if not query:
                    print("[Error] Empty query after stripping flags.")
                    continue

                show_logs_this = self.show_logs or logs_override

                result = self.process_query(query, want_report=want_report, want_pdf=want_pdf,
                                            want_draft=want_draft, show_logs=show_logs_this, want_research=want_research)
                self.display_result(result, show_logs=show_logs_this)

                # Remember query for this feedback_id so feedback loop has context
                fid = result.get("validation", {}).get("feedback_id")
                if fid:
                    self._query_by_fid[fid] = query

            except KeyboardInterrupt:
                print("\n\nInterrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n[Error] {e}")

    def _handle_feedback(self, raw: str):
        """Record user feedback as JSON-lines with query context.

        The feedback is stored in ``feedback_log.jsonl`` so
        :func:`autogen_agent.load_feedback_context` can inject it into
        future LLM prompts — closing the feedback loop.
        """
        parts = raw.split(None, 2)
        if len(parts) < 2:
            print("Usage: feedback <FEEDBACK_ID> [optional description]")
            return
        fid = parts[1].upper()
        issue = parts[2] if len(parts) > 2 else input("Describe the issue: ").strip()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        original_query = self._query_by_fid.get(fid, "")
        entry = {
            "timestamp": timestamp,
            "feedback_id": fid,
            "query": original_query,
            "issue": issue,
        }
        try:
            from autogen_agent import FEEDBACK_FILE
            with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            print(f"[Feedback] ✅ Logged for ID {fid}. Thank you!")
            if original_query:
                print(f"[Feedback] Context: \"{original_query[:60]}\"")
            print("[Feedback] Your feedback will inform future research responses.")
        except Exception as e:
            print(f"[Feedback] Could not save feedback: {e}")

    def show_help(self):
        """Show help information."""
        print("""
Available Commands:
  - Type any legal question to research
  - 'quit' / 'exit'   — Exit the program
  - 'help'            — Show this message
  - 'feedback <ID> [description]' — Report a hallucination or error

Inline Flags (append to any query):
  --report              Generate a full structured legal report
  --pdf                 Generate a full report AND save it as a PDF file
  --draft [type]        Generate a legal document draft
  --research            Include academic papers from Springer Nature in research
  --logs                Show detailed agent logs for this query

Draft Types (use with --draft):
  writ / writ_petition  Writ Petition under Article 226/32
  notice / legal_notice Legal Notice (civil / contract disputes)
  rti                   RTI Application under RTI Act, 2005
  complaint             Formal Complaint (consumer / police / NHRC)
  affidavit             Sworn Affidavit for court filing
  pil                   Public Interest Litigation petition

Important:
  - This system ONLY answers questions about Indian law and jurisdiction
  - Queries about other jurisdictions will be rejected

Anti-Hallucination (XAIValidationAgent — always active):
  ✅ Factual Grounding    — answers linked to real Indian legal sources
  ✅ Citation Enforcement — every claim must cite a case/article/section
  ✅ IK Cross-Verification — case citations verified against Indian Kanoon API
  ✅ Scope Limiting       — restricted to summarisation, no invented law
  ✅ Feedback Loop        — your feedback is injected into future LLM prompts
  ✅ User Feedback        — every answer has a Feedback ID to report issues

Example Queries:
  What is Article 21?
  Explain Right to Equality --report
  What are Fundamental Rights? --pdf
  Explain judicial review in India --logs
  Provide research papers on money laundering --research
  Draft a petition for Article 21 violation --draft writ
  File an RTI about police encounters --draft rti
  Send a legal notice for breach of contract --draft notice

Global CLI Flags:
  --logs    Always show agent logs
  --report  Always generate full structured report
  --pdf     Always generate full report + PDF
        """)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Constitutional Law Research System with AutoGen + Advanced XAI"
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Direct query (optional, runs interactive mode if not provided)"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate a full structured report instead of a concise answer"
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Generate a full report AND save it as a PDF file"
    )
    parser.add_argument(
        "--draft",
        nargs="?",
        const="writ_petition",
        default=None,
        metavar="TYPE",
        help="Generate a legal draft (writ_petition, legal_notice, rti, complaint, affidavit, pil)"
    )
    parser.add_argument(
        "--logs",
        action="store_true",
        help="Show detailed agent reasoning logs"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    cli = ConstitutionalLawCLI(show_logs=args.logs)

    if not cli.initialize():
        print("[Error] Failed to initialize system. Check your API keys.")
        sys.exit(1)

    if args.query:
        result = cli.process_query(
            args.query,
            want_report=args.report,
            want_pdf=args.pdf,
            want_draft=args.draft,
            show_logs=args.logs
        )
        cli.display_result(result, show_logs=args.logs)
    else:
        cli.interactive_mode()


if __name__ == "__main__":
    main()

