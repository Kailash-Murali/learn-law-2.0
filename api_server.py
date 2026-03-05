"""
FastAPI Service Layer – HTTP bridge between the Next.js front-end
and the Python AutoGen research backend.

Run:
    uvicorn api_server:app --reload --port 8000
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import os

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from cli_adapter import ResearchAdapter
from config import Config

# ---------------------------------------------------------------------------
#  Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-20s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Pydantic request / response models
# ---------------------------------------------------------------------------

class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000, description="Legal research query")
    mode: str | None = Field(None, description="Query mode tag, e.g. [research], [draft], [reports]")
    draft_type: str | None = Field(None, description="Draft sub-type when mode is [draft]")


class ResearchResponse(BaseModel):
    id: str
    status: str
    query: str
    documentation: Optional[Dict[str, Any]] = None
    agent_traces: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    ui_payload: Optional[Dict[str, Any]] = None
    pdf_path: Optional[str] = None
    docx_path: Optional[str] = None
    error: Optional[str] = None
    timestamp: str


class ParseRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)


class HealthResponse(BaseModel):
    status: str
    missing_keys: List[str]
    adapter_ready: bool
    timestamp: str


class ErrorDetail(BaseModel):
    detail: str


# ---------------------------------------------------------------------------
#  FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Constitutional Law Research API",
    version="1.0.0",
    description="Bridge between the learn-law Next.js UI and the AutoGen research backend.",
)

# CORS – allow the Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
#  Singleton adapter
# ---------------------------------------------------------------------------

_adapter: ResearchAdapter | None = None


def _get_adapter() -> ResearchAdapter:
    global _adapter
    if _adapter is None:
        _adapter = ResearchAdapter()
        if not _adapter.initialise():
            logger.warning("Adapter initialised with missing keys – some endpoints may fail.")
    return _adapter


# ---------------------------------------------------------------------------
#  Routes
# ---------------------------------------------------------------------------

@app.get("/api/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """Return system health and missing secret status."""
    adapter = _get_adapter()
    return HealthResponse(
        status="ok" if adapter.ready else "degraded",
        missing_keys=Config.validate(),
        adapter_ready=adapter.ready,
        timestamp=datetime.utcnow().isoformat(),
    )


@app.post(
    "/api/research",
    response_model=ResearchResponse,
    responses={500: {"model": ErrorDetail}},
    tags=["research"],
)
async def run_research(body: ResearchRequest):
    """
    Execute a full research pipeline for the given query.
    Returns structured documentation, XAI report, and agent traces.
    """
    adapter = _get_adapter()
    if not adapter.ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Research system not initialised. Check API keys via /api/health.",
        )

    result = adapter.research(body.query, mode=body.mode, draft_type=body.draft_type)

    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Unknown error"),
        )

    return ResearchResponse(
        id=uuid.uuid4().hex,
        status=result["status"],
        query=result["query"],
        documentation=result.get("documentation"),
        agent_traces=result.get("agent_traces"),
        validation=result.get("validation"),
        ui_payload=result.get("ui_payload"),
        pdf_path=result.get("pdf_path"),
        docx_path=result.get("docx_path"),
        error=result.get("error"),
        timestamp=datetime.utcnow().isoformat(),
    )


@app.post(
    "/api/parse",
    tags=["research"],
    responses={500: {"model": ErrorDetail}},
)
async def parse_query(body: ParseRequest):
    """Parse a legal query without running full research."""
    adapter = _get_adapter()
    if not adapter.ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Research system not initialised.",
        )
    try:
        parsed = adapter.parse_query(body.query)
        return {"status": "ok", "parsed": parsed}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/download", tags=["files"])
async def download_file(path: str = Query(..., description="Server-side file path")):
    """Download a generated file (PDF or DOCX) by its server path."""
    resolved = os.path.realpath(path)
    # Prevent path-traversal: file must exist under the project directory
    project_root = os.path.realpath(os.path.dirname(__file__))
    if not resolved.startswith(project_root + os.sep):
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.isfile(resolved):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(resolved, filename=os.path.basename(resolved))
