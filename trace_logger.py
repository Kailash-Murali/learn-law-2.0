import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional, List

# Assuming ConstitutionalLawDB is in database.py
from database import ConstitutionalLawDB


class TraceLogger:
    """Helper for recording structured logs, artefacts, and decisions."""

    def __init__(self, db: ConstitutionalLawDB):
        self.db = db

    def log_event(
        self,
        agent: str,
        event_type: str,
        payload: Dict[str, Any],
        request_id: Optional[int] = None,
        phase: Optional[str] = None,
    ) -> int:
        payload_with_meta = {
            **payload,
            "logged_at": datetime.now().isoformat(),
            "payload_hash": self._hash_payload(payload),
        }
        return self.db.insert_trace_log(
            agent=agent,
            event_type=event_type,
            payload=payload_with_meta,
            request_id=request_id,
            phase=phase,
        )

    def snapshot_artefact(
        self,
        agent: str,
        artefact_type: str,
        content: Dict[str, Any],
        request_id: Optional[int] = None,
    ) -> int:
        wrapped_content = {
            "captured_at": datetime.now().isoformat(),
            "content": content,
            "content_hash": self._hash_payload(content),
        }
        return self.db.insert_artefact_snapshot(
            agent=agent,
            artefact_type=artefact_type,
            content=wrapped_content,
            request_id=request_id,
        )

    def record_decision(
        self,
        agent: str,
        decision_type: str,
        metadata: Dict[str, Any],
        request_id: Optional[int] = None,
        rationale: Optional[str] = None,
    ) -> int:
        enriched_metadata = {
            **metadata,
            "recorded_at": datetime.now().isoformat(),
        }
        return self.db.insert_decision_metadata(
            agent=agent,
            decision_type=decision_type,
            metadata=enriched_metadata,
            request_id=request_id,
            rationale=rationale,
        )

    def _hash_payload(self, payload: Dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    # --- New methods to expose DB retrieval functionality ---

    def get_full_request_trace(self, request_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all trace events, decisions, and artefact snapshots for a given request_id,
        sorted chronologically. Delegates to ConstitutionalLawDB.
        """
        return self.db.get_combined_request_trace_data(request_id)

    def get_artefact_snapshots_for_request(self, request_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves summary details for all artefact snapshots for a given request_id.
        Delegates to ConstitutionalLawDB.
        """
        return self.db.get_artefact_snapshots_for_request(request_id)

    def get_artefact_content_by_id(self, artefact_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves the full 'content' of an artefact snapshot by its ID.
        Delegates to ConstitutionalLawDB.
        """
        return self.db.get_artefact_full_content_by_id(artefact_id)