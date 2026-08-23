# -*- coding: utf-8 -*-
"""FAQ-aware reply generation for customer consultations."""

from __future__ import annotations

from typing import Any

try:
    from .intent_engine import classify_intent
except ImportError:
    from intent_engine import classify_intent

FAQ: list[dict[str, Any]] = [
    {"question": "订单发货了没", "keywords": ["订单", "发货"], "answer": "您的订单正在按计划交货，具体进度可在「订单进度看板」中按订单号查询。若超过承诺交期，请提供订单号，我帮您核对物流情况。"},
    {"question": "电机异响怎么处理", "keywords": ["电机", "异响"], "answer": "电机异响通常是轴承磨损或装配间隙问题。建议先断电并录制异常声音，联系售后报修，我们会按故障类型指派专业工程师处理。"},
    {"question": "开票流程", "keywords": ["发票", "开票"], "answer": "请提供发票抬头、税号和开票金额，我们会核对订单后开具发票。一般开票周期为1-3个工作日。"},
    {"question": "退货政策", "keywords": ["退货", "退换"], "answer": "支持七天无理由退换货，但需保持商品完好并附原包装。非质量问题的退货运费由客户承担，质量问题由我们承担。"},
    {"question": "产品参数", "keywords": ["参数", "功率", "型号"], "answer": "请提供具体产品型号或联系我们索取完整参数表，我们会依据材质、功率和尺寸给出准确建议。"},
]


def _degree(text: str, keywords: list[str]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def answer_consult(text: str, knowledge_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Return a matched FAQ answer or a routed human-handoff reply."""
    if not text or not text.strip():
        raise ValueError("咨询文本不能为空")
    intent = classify_intent(text)
    # Knowledge-aware reply takes priority for after-sale intents so structured
    # maintenance knowledge is surfaced before generic FAQ keyword matching.
    if intent["intent"] == "after_sale" and knowledge_records:
        for entry in knowledge_records:
            problem = str(entry.get("problem") or "")
            tags = entry.get("tags", [])
            if (problem and problem in text) or any(tag in text for tag in tags):
                cause = str(entry.get("cause") or "").strip()
                solution = str(entry.get("solution") or "").strip()
                custom = f"根据历史维修知识：{problem}"
                if cause:
                    custom += f"（原因：{cause}）"
                if solution:
                    custom += f"，处理方案：{solution}"
                return {
                    "matched_faq": None,
                    "answer": custom,
                    "confidence": 0.72,
                    "intent": intent["intent"],
                    "intent_label": intent["intent_label"],
                    "knowledge_hit": True,
                    "method": "knowledge-enhanced-v1",
                }
    scored = []
    for faq in FAQ:
        degree = _degree(text, faq["keywords"])
        if degree:
            scored.append((degree, faq))
    scored.sort(key=lambda item: item[0], reverse=True)
    if scored and scored[0][0] >= 2:
        degree, faq = scored[0]
        return {
            "matched_faq": faq["question"],
            "answer": faq["answer"],
            "confidence": round(min(0.95, 0.6 + degree * 0.12), 3),
            "intent": intent["intent"],
            "intent_label": intent["intent_label"],
            "method": "faq-keyword-v1",
        }
    return {
        "matched_faq": None,
        "answer": f"您的咨询涉及「{intent['intent_label']}」，为保证准确性，已为您转接人工客服，请保持电话畅通。",
        "confidence": 0.5,
        "intent": intent["intent"],
        "intent_label": intent["intent_label"],
        "knowledge_hit": False,
        "method": "faq-keyword-routed-v1",
    }
