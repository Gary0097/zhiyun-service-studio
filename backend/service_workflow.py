# -*- coding: utf-8 -*-
"""Persistent, auditable after-sale ticket and knowledge workflow."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .ticket_engine import recommend_engineer, route_ticket
except ImportError:
    from ticket_engine import recommend_engineer, route_ticket

DEFAULT_ENGINEERS = [
    {"name": "张工", "skills": ["电机", "异响", "轴承"], "active_tickets": 2},
    {"name": "李工", "skills": ["压铸", "裂纹", "气孔"], "active_tickets": 1},
    {"name": "王工", "skills": ["控制器", "接线", "发烫"], "active_tickets": 4},
    {"name": "赵工", "skills": ["装配", "漏油", "异响"], "active_tickets": 0},
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ServiceWorkflowStore:
    """SQLite repository for tickets and knowledge artifacts."""

    def __init__(self, path: str | Path | None = None) -> None:
        configured = path or os.getenv("SERVICE_STUDIO_DB")
        self.path = Path(configured) if configured else Path.home() / ".zhiyun-service-studio" / "service.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path))
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY, customer_name TEXT NOT NULL, product TEXT, fault_type TEXT,
                    description TEXT NOT NULL, team TEXT, recommended_engineer TEXT,
                    recommendation_json TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ticket_reviews (
                    id TEXT PRIMARY KEY, ticket_id TEXT NOT NULL REFERENCES tickets(id),
                    action TEXT NOT NULL, reviewer TEXT NOT NULL, note TEXT, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS knowledge_artifacts (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, entries_json TEXT NOT NULL,
                    status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS knowledge_reviews (
                    id TEXT PRIMARY KEY, artifact_id TEXT NOT NULL REFERENCES knowledge_artifacts(id),
                    action TEXT NOT NULL, reviewer TEXT NOT NULL, note TEXT, created_at TEXT NOT NULL
                );
            """)

    def create_ticket(self, customer_name: str, description: str, product: str = "",
                      fault_type: str = "") -> dict[str, Any]:
        if not customer_name.strip() or not description.strip():
            raise ValueError("客户名称和问题描述不能为空")
        ticket_id, now = str(uuid.uuid4()), _now()
        ticket = {"customer_name": customer_name.strip(), "product": product, "fault_type": fault_type,
                  "description": description.strip()}
        routed = route_ticket(ticket)
        recommendation = recommend_engineer({**ticket, **routed}, DEFAULT_ENGINEERS)
        best = recommendation["recommendations"][0]
        with closing(self._connect()) as db, db:
            db.execute(
                "INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (ticket_id, ticket["customer_name"], product, fault_type, ticket["description"],
                 routed["team"], best["name"], json.dumps(recommendation, ensure_ascii=False),
                 "pending_review", now, now),
            )
        return self.get_ticket(ticket_id)

    def get_ticket(self, ticket_id: str) -> dict[str, Any]:
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
            if not row:
                raise KeyError(ticket_id)
            reviews = [dict(item) for item in db.execute(
                "SELECT * FROM ticket_reviews WHERE ticket_id=? ORDER BY created_at", (ticket_id,)
            )]
            result = dict(row)
            result["recommendation"] = json.loads(result.pop("recommendation_json"))
            result["reviews"] = reviews
            return result

    def list_tickets(self, limit: int = 100) -> dict[str, Any]:
        with closing(self._connect()) as db, db:
            rows = db.execute("SELECT * FROM tickets ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return {"tickets": [dict(row) for row in rows], "count": len(rows)}

    def review_ticket(self, ticket_id: str, action: str, reviewer: str,
                      engineer: str | None = None, note: str | None = None) -> dict[str, Any]:
        if action not in {"accept", "reject"}:
            raise ValueError("工单处理动作必须是 accept 或 reject")
        if not reviewer.strip():
            raise ValueError("审阅人不能为空")
        ticket = self.get_ticket(ticket_id)
        if action == "accept" and not engineer:
            raise ValueError("接受工单前必须确认分派工程师")
        now = _now()
        with closing(self._connect()) as db, db:
            db.execute("INSERT INTO ticket_reviews VALUES (?,?,?,?,?,?)",
                       (str(uuid.uuid4()), ticket_id, action, reviewer.strip(), note, now))
            db.execute("UPDATE tickets SET status=?, recommended_engineer=?, updated_at=? WHERE id=?",
                       ("accepted" if action == "accept" else "rejected", engineer or ticket["recommended_engineer"], now, ticket_id))
        return self.get_ticket(ticket_id)

    def create_knowledge_artifact(self, title: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
        artifact_id, now = str(uuid.uuid4()), _now()
        with closing(self._connect()) as db, db:
            db.execute("INSERT INTO knowledge_artifacts VALUES (?,?,?,?,?,?)",
                       (artifact_id, title, json.dumps(entries, ensure_ascii=False), "pending_review", now, now))
        return self.get_knowledge_artifact(artifact_id)

    def get_knowledge_artifact(self, artifact_id: str) -> dict[str, Any]:
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT * FROM knowledge_artifacts WHERE id=?", (artifact_id,)).fetchone()
            if not row:
                raise KeyError(artifact_id)
            reviews = [dict(item) for item in db.execute(
                "SELECT * FROM knowledge_reviews WHERE artifact_id=? ORDER BY created_at", (artifact_id,)
            )]
            result = dict(row)
            result["entries"] = json.loads(result.pop("entries_json"))
            result["reviews"] = reviews
            return result

    def review_knowledge(self, artifact_id: str, action: str, reviewer: str,
                         note: str | None = None) -> dict[str, Any]:
        if action not in {"accept", "reject"}:
            raise ValueError("知识审阅动作必须是 accept 或 reject")
        if not reviewer.strip():
            raise ValueError("审阅人不能为空")
        self.get_knowledge_artifact(artifact_id)
        now = _now()
        with closing(self._connect()) as db, db:
            db.execute("INSERT INTO knowledge_reviews VALUES (?,?,?,?,?,?)",
                       (str(uuid.uuid4()), artifact_id, action, reviewer.strip(), note, now))
            db.execute("UPDATE knowledge_artifacts SET status=?, updated_at=? WHERE id=?",
                       ("accepted" if action == "accept" else "rejected", now, artifact_id))
        return self.get_knowledge_artifact(artifact_id)

    def export_knowledge(self, artifact_id: str) -> tuple[str, str]:
        artifact = self.get_knowledge_artifact(artifact_id)
        if artifact["status"] != "accepted":
            raise ValueError("只有已接受的知识库可以导出")
        return json.dumps(artifact, ensure_ascii=False, indent=2), "application/json"
