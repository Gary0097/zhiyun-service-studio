# -*- coding: utf-8 -*-
"""After-sale ticket routing and engineer recommendation."""

from __future__ import annotations

from collections import Counter
from typing import Any

TEAM_RULES: list[tuple[str, list[str]]] = [
    ("电机组", ["电机", "异响", "转速"]),
    ("压铸组", ["压铸", "裂纹", "气孔"]),
    ("装配组", ["装配", "漏油", "异响"]),
    ("电气组", ["控制器", "接线", "烧机", "发烫"]),
    ("质检组", ["质检", "外观", "瑕疵"]),
]


def _level(score: int) -> str:
    return "high" if score >= 80 else "medium" if score >= 60 else "low"


def route_ticket(ticket: dict[str, Any]) -> dict[str, Any]:
    """Route a ticket to a team based on fault type keywords."""
    text = f"{ticket.get('fault_type','')}{ticket.get('description','')}{ticket.get('product','')}"
    for team, keywords in TEAM_RULES:
        for keyword in keywords:
            if keyword in text:
                return {"team": team, "match_keyword": keyword, "reason": f"命中故障关键词「{keyword}」"}
    return {"team": "综合组", "match_keyword": None, "reason": "未命中专项关键词，转综合组人工分派"}


def recommend_engineer(ticket: dict[str, Any], engineers: list[dict[str, Any]]) -> dict[str, Any]:
    """Pick the best engineer by skill overlap and current workload."""
    if not engineers:
        raise ValueError("工程师列表不能为空")
    text = f"{ticket.get('fault_type','')}{ticket.get('description','')}{ticket.get('product','')}"
    scored = []
    for engineer in engineers:
        skills = set(engineer.get("skills", []))
        matched = [skill for skill in skills if skill in text]
        load = int(engineer.get("active_tickets", 0) or 0)
        skill_score = len(matched) * 30
        load_score = max(0, 100 - load * 8)
        score = min(100, 35 + skill_score + load_score)
        scored.append({
            **engineer,
            "matched_skills": matched,
            "active_tickets": load,
            "score": score,
            "level": _level(score),
        })
    scored.sort(key=lambda item: item["score"], reverse=True)
    return {"recommendations": scored, "method": "skill-overlap-workload-v1"}
