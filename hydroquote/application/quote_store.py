"""Durable quote store (single-instance MVP: JSON files on disk)."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class QuoteStore:
    def __init__(self, root: Path | None = None):
        self.root = root or Path("data") / "quotes"
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _path(self, quote_id: str) -> Path:
        safe = quote_id.replace("/", "_").replace("..", "_")
        return self.root / f"{safe}.json"

    def _read_unlocked(self, quote_id: str) -> Optional[dict[str, Any]]:
        path = self._path(quote_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def create(
        self,
        *,
        tenant_id: str,
        request_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        with self._lock:
            existing = self.find_by_request_id(tenant_id, request_id)
            if existing:
                return existing
            quote_id = f"Q-{uuid.uuid4().hex[:12].upper()}"
            record = {
                "quote_id": quote_id,
                "tenant_id": tenant_id,
                "request_id": request_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "status": payload.get("status", "processing"),
                "workflow_stage": payload.get("workflow_stage", "customer_inquiry"),
                "workflow_path": payload.get("workflow_path"),
                "revision": 1,
                "data": payload,
                "audit": [{"event": "created", "at": datetime.now(timezone.utc).isoformat()}],
            }
            self._write(record)
            return record

    def get(self, quote_id: str, tenant_id: str | None = None) -> Optional[dict[str, Any]]:
        with self._lock:
            record = self._read_unlocked(quote_id)
        if record is None:
            return None
        if tenant_id is not None and record.get("tenant_id") != tenant_id:
            return None
        return record

    def update(self, quote_id: str, tenant_id: str, mutator) -> dict[str, Any]:
        with self._lock:
            record = self._read_unlocked(quote_id)
            if not record or record.get("tenant_id") != tenant_id:
                raise KeyError(quote_id)
            mutator(record)
            record["updated_at"] = datetime.now(timezone.utc).isoformat()
            record["revision"] = int(record.get("revision", 1)) + 1
            self._write(record)
            return record

    def find_by_request_id(self, tenant_id: str, request_id: str) -> Optional[dict[str, Any]]:
        for path in self.root.glob("Q-*.json"):
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if rec.get("tenant_id") == tenant_id and rec.get("request_id") == request_id:
                return rec
        return None

    def _write(self, record: dict[str, Any]) -> None:
        path = self._path(record["quote_id"])
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
        tmp.replace(path)
