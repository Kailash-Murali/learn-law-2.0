"""
CLI Adapter – Adapter pattern isolating the AutoGen research system
so it can be called from both the interactive CLI and the FastAPI layer.

All public methods return plain dicts (JSON-serialisable).
No print() calls – callers decide how to surface output.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from config import Config
from exceptions import ConstitutionalLawException

logger = logging.getLogger(__name__)


class ResearchAdapter:
    """
    Thin, stateless adapter around AutoGenLegalResearch.

    Usage:
        adapter = ResearchAdapter()
        adapter.initialise()               # call once
        result = adapter.research(query)    # call many times
    """

    def __init__(self):
        self._system = None  # lazy
        self._initialised = False

    # ------------------------------------------------------------------ #
    #  Lifecycle
    # ------------------------------------------------------------------ #

    def initialise(self) -> bool:
        """
        Validate config & boot the AutoGen system.
        Returns True on success, False on failure.
        """
        missing = Config.validate()
        if missing:
            logger.error("Missing required secrets: %s", ", ".join(missing))
            return False

        try:
            from autogen_agent import AutoGenLegalResearch

            self._system = AutoGenLegalResearch()
            self._initialised = True
            logger.info("ResearchAdapter initialised")
            return True
        except Exception as exc:
            logger.exception("Failed to initialise research system: %s", exc)
            return False

    @property
    def ready(self) -> bool:
        return self._initialised and self._system is not None

    # ------------------------------------------------------------------ #
    #  Core operations
    # ------------------------------------------------------------------ #

    def research(self, query: str, *, mode: str | None = None, draft_type: str | None = None) -> Dict[str, Any]:
        """
        Run a full research pipeline for *query*.

        Parameters
        ----------
        mode       : optional mode tag e.g. "[research]", "[draft]", "[reports]"
        draft_type : draft sub-type when mode is "[draft]"

        Returns a normalised result dict:
            {
                "status":  "success" | "error",
                "query":   <original query>,
                "documentation": { ... },
                "agent_traces": { ... },
                "error": <str | None>
            }
        """
        self._ensure_ready()

        want_research = mode == "[research]"
        want_draft = draft_type if mode == "[draft]" else None
        # [research] combines Springer papers + full report + PDF in one response
        want_report = mode in ("[research]", "[reports]")
        want_pdf = mode in ("[research]", "[reports]")
        want_contrastive = mode == "[contrastive]"

        try:
            raw = self._system.run_research(
                query,
                want_research=want_research,
                want_report=want_report,
                want_pdf=want_pdf,
                want_draft=want_draft,
                want_contrastive=want_contrastive,
            )
            return self._normalise(query, raw)
        except ConstitutionalLawException as exc:
            logger.error("Research error for query '%s': %s", query, exc)
            return self._error(query, str(exc))
        except Exception as exc:
            logger.exception("Unexpected error for query '%s'", query)
            return self._error(query, str(exc))

    def parse_query(self, query: str) -> Dict[str, Any]:
        """Parse only (no research or documentation)."""
        self._ensure_ready()
        return self._system.parse_query(query)

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _ensure_ready(self):
        if not self.ready:
            raise RuntimeError(
                "ResearchAdapter not initialised – call initialise() first."
            )

    @staticmethod
    def _normalise(query: str, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": raw.get("status", "success"),
            "query": query,
            "documentation": raw.get("documentation"),
            "agent_traces": raw.get("agent_reasoning_traces"),
            "validation": raw.get("validation"),
            "ui_payload": raw.get("ui_payload"),
            "pdf_path": raw.get("pdf_path"),
            "docx_path": raw.get("docx_path"),
            "error": raw.get("error"),
        }

    @staticmethod
    def _error(query: str, message: str) -> Dict[str, Any]:
        return {
            "status": "error",
            "query": query,
            "documentation": None,
            "agent_traces": None,
            "validation": None,
            "ui_payload": None,
            "pdf_path": None,
            "docx_path": None,
            "error": message,
        }
