"""
FastAPI Service Layer – HTTP bridge between the Next.js front-end
and the Python AutoGen research backend.

Run:
    uvicorn api_server:app --reload --port 8000
"""

from __future__ import annotations

import logging
import json
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
from agents.shap_service import get_shap_service
from agents.dice_service import get_dice_service
from agents.attention_proxy_service import compute_attention_map
from agents.surrogate_tree_service import get_surrogate_service

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


class FeedbackRequest(BaseModel):
    message_id: str
    vote: str = Field(..., pattern="^(up|down)$")
    comment: Optional[str] = None
    query: Optional[str] = None
    xai_feature_used: Optional[str] = None
    time_spent_viewing_ms: Optional[int] = None
    user_rating: Optional[int] = Field(None, ge=1, le=5)


class ConfidenceBreakdownRequest(BaseModel):
    law_text: str = Field(..., min_length=1, max_length=5000)
    context: str = Field("", max_length=5000)


class CounterfactualRequest(BaseModel):
    case_features: Dict[str, Any]


class AttentionMapRequest(BaseModel):
    answer_sentences: List[str]
    citations: List[Dict[str, str]]


class SurrogateTreeRequest(BaseModel):
    validation_features: Dict[str, float]


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


# ---------------------------------------------------------------------------
#  XAI Endpoints
# ---------------------------------------------------------------------------


@app.post("/api/xai/confidence-breakdown", tags=["xai"])
async def confidence_breakdown(body: ConfidenceBreakdownRequest):
    """Return SHAP-based explanation of bad-law confidence score."""
    svc = get_shap_service()
    return svc.explain(body.law_text, body.context)


@app.post("/api/xai/counterfactuals", tags=["xai"])
async def counterfactuals(body: CounterfactualRequest):
    """Generate diverse counterfactual explanations via DiCE."""
    svc = get_dice_service()
    return svc.generate(body.case_features, k=3)


@app.post("/api/xai/attention-map", tags=["xai"])
async def attention_map(body: AttentionMapRequest):
    """Return TF-IDF cosine similarity scores as attention proxy."""
    citation_texts = [
        {"name": c.get("name", ""), "url": c.get("url", ""), "text": c.get("text", c.get("name", ""))}
        for c in body.citations
    ]
    return compute_attention_map(body.answer_sentences, citation_texts)


@app.post("/api/xai/surrogate-tree", tags=["xai"])
async def surrogate_tree(body: SurrogateTreeRequest):
    """Return surrogate decision tree path for validation logic."""
    svc = get_surrogate_service()
    return svc.explain(body.validation_features)


# ---------------------------------------------------------------------------
#  Feedback
# ---------------------------------------------------------------------------

FEEDBACK_FILE = "feedback_log.jsonl"


@app.post("/api/feedback", tags=["feedback"])
async def submit_feedback(body: FeedbackRequest):
    """Append user feedback to the feedback log for future context injection."""
    entry: Dict[str, Any] = {
        "query": body.query or "",
        "issue": body.comment or "",
        "vote": body.vote,
        "message_id": body.message_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if body.xai_feature_used:
        entry["xai_feature_used"] = body.xai_feature_used
    if body.time_spent_viewing_ms is not None:
        entry["time_spent_viewing_ms"] = body.time_spent_viewing_ms
    if body.user_rating is not None:
        entry["user_rating"] = body.user_rating
    try:
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.warning("Could not write feedback: %s", exc)
    return {"status": "ok"}


@app.get("/api/telemetry/xai-summary", tags=["telemetry"])
async def xai_telemetry_summary():
    """Aggregated XAI feature telemetry from feedback log."""
    import os
    if not os.path.isfile(FEEDBACK_FILE):
        return {"features": {}}

    from collections import defaultdict
    feature_stats: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "total_time_ms": 0, "ratings": []}
    )
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                feat = rec.get("xai_feature_used")
                if not feat:
                    continue
                stats = feature_stats[feat]
                stats["count"] += 1
                t = rec.get("time_spent_viewing_ms")
                if isinstance(t, (int, float)):
                    stats["total_time_ms"] += t
                r = rec.get("user_rating")
                if isinstance(r, int):
                    stats["ratings"].append(r)
    except Exception as exc:
        logger.warning("Telemetry read error: %s", exc)
        return {"features": {}}

    summary: Dict[str, Any] = {}
    for feat, st in feature_stats.items():
        avg_time = round(st["total_time_ms"] / st["count"]) if st["count"] else 0
        ratings = st["ratings"]
        acceptance = round(sum(1 for r in ratings if r >= 4) / len(ratings) * 100, 1) if ratings else None
        summary[feat] = {
            "view_count": st["count"],
            "avg_time_ms": avg_time,
            "acceptance_rate_pct": acceptance,
        }
    return {"features": summary}
