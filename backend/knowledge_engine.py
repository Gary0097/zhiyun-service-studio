# -*- coding: utf-8 -*-
"""Knowledge extraction and optimization from real service records."""

from __future__ import annotations

import hashlib
import re
from typing import Any

TAG_KEYWORDS: list[tuple[str, str]] = [
    ("售后报修", "报修"),
    ("质量缺陷", "缺陷"),
    ("安装调试", "安装"),
    ("使用说明", "使用"),
    ("物流配送", "物流"),
    ("退换货", "退货"),
    ("发票", "发票"),
]


def _tag(text: str) -> list[str]:
    tags = []
    for label, keyword in TAG_KEYWORDS:
        if keyword in text:
            tags.append(label)
    return tags[:5] if tags else ["其他"]


def _validate_record(record: dict[str, Any]) -> bool:
    return any(str(record.get(key, "")).strip() for key in ("fault_type", "problem", "solution"))


def extract_knowledge(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Turn service records into structured, deduplicated knowledge entries."""
    if len(records) > 5000:
        raise ValueError("单次最多处理5000条记录")
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        if not _validate_record(record):
            continue
        problem = str(record.get("fault_type") or record.get("problem") or "").strip()
        cause = str(record.get("cause") or "").strip()
        solution = str(record.get("solution") or "").strip()
        product = str(record.get("product") or "").strip()
        engineer = str(record.get("engineer") or "").strip()
        fingerprint = hashlib.sha1(
            f"{problem}|{solution}|{product}".encode("utf-8"), usedforsecurity=False
        ).hexdigest()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        body = f"{problem} {cause} {solution} {product} {engineer}".strip()
        entries.append({
            "knowledge_id": fingerprint[:12],
            "problem": problem or "未记录故障",
            "cause": cause or "",
            "solution": solution or "",
            "product": product,
            "engineer": engineer,
            "tags": _tag(body),
            "source_record": record.get("record_id", ""),
        })
    return {"entries": entries, "count": len(entries), "method": "rule-based-extraction-v1"}


def optimize_knowledge(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Score knowledge by tag coverage, solution completeness and recency."""
    if len(entries) > 10000:
        raise ValueError("知识条目数量超限")
    ranked = []
    for entry in entries:
        score = 50
        if entry.get("solution"):
            score += 20
        if entry.get("cause"):
            score += 15
        score += min(len(entry.get("tags", [])) * 3, 15)
        ranked.append({**entry, "score": min(score, 100)})
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return {"total": len(ranked), "entries": ranked, "method": "optimization-v1"}
