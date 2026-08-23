# -*- coding: utf-8 -*-
"""Explainable customer-consultation intent classification."""

from __future__ import annotations

import re
from typing import Any

INTENTS = {
    "order_status": "订单查询",
    "after_sale": "售后报修",
    "financial_support": "财务支持",
    "return_exchange": "退换货",
    "complaint": "投诉建议",
    "product_info": "产品咨询",
    "shipping": "物流配送",
    "other": "其他",
}

RULES: dict[str, list[str]] = {
    "order_status": ["订单", "发货", "进度", "下单", "付款了", "物流到哪"],
    "after_sale": ["维修", "报修", "坏了", "故障", "异响", "不工作", "售后"],
    "financial_support": ["发票", "开票", "退款", "收费", "发票抬头", "报销"],
    "return_exchange": ["退货", "换货", "退回", "退换", "七天"],
    "complaint": ["投诉", "差评", "态度", "太慢", "不满", "客服"],
    "product_info": ["型号", "参数", "规格", "功率", "怎么用", "功能", "多少钱"],
    "shipping": ["快递", "运费", "到货", "签收", "配送", "物流"],
}

ORDER_NO_PATTERN = re.compile(r"\b([A-Z]{0,4}\d{6,})\b")
PRODUCT_KEYWORDS = ["电机", "压铸", "齿轮箱", "铝件", "控制器", "减速机", "外壳", "轴承"]


def _extract_entities(text: str) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    for match in ORDER_NO_PATTERN.finditer(text):
        entities.append({"type": "order_no", "value": match.group(1), "source": "文本匹配"})
    for keyword in PRODUCT_KEYWORDS:
        if keyword in text:
            entities.append({"type": "product", "value": keyword, "source": "产品词库"})
    if re.search(r"\b\d{6,8}\b", text):
        phone = re.search(r"1[3-9]\d{9}", text)
        if phone:
            entities.append({"type": "phone", "value": phone.group(0), "source": "手机号规则"})
    return entities[:12]


def classify_intent(text: str) -> dict[str, Any]:
    """Return the dominant intent with matched rules and extracted entities."""
    if not text or not text.strip():
        raise ValueError("咨询文本不能为空")
    normalized = text.lower()
    scores = {intent: 0 for intent in INTENTS}
    matched: dict[str, list[str]] = {intent: [] for intent in INTENTS}
    for intent, keywords in RULES.items():
        for keyword in keywords:
            if keyword in normalized:
                scores[intent] += 1
                matched[intent].append(keyword)
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        best = "other"
    total = sum(scores.values())
    confidence = 0.99 if best == "other" and total == 0 else round(scores[best] / max(total, 1), 3)
    return {
        "intent": best,
        "intent_label": INTENTS[best],
        "confidence": confidence,
        "matched_keywords": matched[best],
        "all_scores": {INTENTS[k]: v for k, v in scores.items() if v},
        "entities": _extract_entities(text),
        "method": "rule-based-explainable-v1",
    }
