# -*- coding: utf-8 -*-
"""Service Studio HTTP and Agent entrypoint."""

from __future__ import annotations

import json
import sys
import sqlite3
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from qwenpaw.plugins.api import PluginApi

import httpx
from uuid import uuid4
from fastapi.responses import StreamingResponse

try:
    from .answer_engine import answer_consult
    from .intent_engine import classify_intent
    from .knowledge_engine import extract_knowledge, optimize_knowledge
    from .service_workflow import ServiceWorkflowStore
except ImportError:
    backend_dir = str(Path(__file__).resolve().parent)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from answer_engine import answer_consult
    from intent_engine import classify_intent
    from knowledge_engine import extract_knowledge, optimize_knowledge
    from service_workflow import ServiceWorkflowStore

router = APIRouter()
PLUGIN_VERSION = "0.3.0"


def _store() -> ServiceWorkflowStore:
    try:
        return ServiceWorkflowStore()
    except (OSError, sqlite3.Error) as exc:
        raise HTTPException(status_code=503, detail=f"售后持久化依赖不可用：{exc}") from exc


class TextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


class RecordsRequest(BaseModel):
    records: list[dict[str, Any]] = Field(max_length=5000)


class TicketRequest(BaseModel):
    customer_name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=5000)
    product: str = Field(default="", max_length=200)
    fault_type: str = Field(default="", max_length=200)


class TicketReviewRequest(BaseModel):
    action: str
    reviewer: str = Field(min_length=1, max_length=100)
    engineer: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=2000)


class KnowledgeBuildRequest(BaseModel):
    records: list[dict[str, Any]] = Field(min_length=1, max_length=5000)
    title: str = Field(default="售后知识库", max_length=200)


class KnowledgeReviewRequest(BaseModel):
    action: str
    reviewer: str = Field(min_length=1, max_length=100)
    note: str | None = Field(default=None, max_length=2000)


class ArtifactReviewRequest(BaseModel):
    action: str
    reviewer: str = Field(min_length=1, max_length=100)
    note: str | None = Field(default=None, max_length=2000)


@router.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "available", "version": PLUGIN_VERSION}


@router.post("/intent/classify")
async def intent_classify(request: TextRequest) -> dict[str, Any]:
    try:
        result = classify_intent(request.text)
        return _store().create_consult_artifact("intent", result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail=f"售后持久化依赖不可用：{exc}") from exc


@router.post("/answer")
async def answer(request: TextRequest) -> dict[str, Any]:
    try:
        result = answer_consult(request.text)
        return _store().create_consult_artifact("answer", result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail=f"售后持久化依赖不可用：{exc}") from exc


@router.get("/artifacts/{artifact_id}")
async def get_consult_artifact(artifact_id: str) -> dict[str, Any]:
    try:
        return _store()._consult_result(artifact_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="工件不存在") from exc


@router.post("/artifacts/{artifact_id}/reviews")
async def review_consult_artifact(artifact_id: str, request: ArtifactReviewRequest) -> dict[str, Any]:
    try:
        return _store().review_consult_artifact(artifact_id, request.action, request.reviewer, request.note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="工件不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/artifacts/{artifact_id}/export")
async def export_consult_artifact(artifact_id: str) -> Response:
    try:
        content, media_type = _store().export_consult_artifact(artifact_id)
        return Response(content=content, media_type=media_type,
                        headers={"Content-Disposition": 'attachment; filename="artifact.json"'})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="工件不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/knowledge/extract")
async def knowledge_extract(request: RecordsRequest) -> dict[str, Any]:
    try:
        return extract_knowledge(request.records)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/knowledge/optimize")
async def knowledge_optimize(request: RecordsRequest) -> dict[str, Any]:
    try:
        return optimize_knowledge(request.records)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/knowledge/artifacts")
async def create_knowledge(request: KnowledgeBuildRequest) -> dict[str, Any]:
    try:
        extracted = extract_knowledge(request.records)
        optimized = optimize_knowledge(extracted["entries"])
        return _store().create_knowledge_artifact(request.title, optimized["entries"])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail=f"售后持久化依赖不可用：{exc}") from exc


@router.get("/knowledge/artifacts/{artifact_id}")
async def get_knowledge(artifact_id: str) -> dict[str, Any]:
    try:
        return _store().get_knowledge_artifact(artifact_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="知识库不存在") from exc


@router.post("/knowledge/artifacts/{artifact_id}/reviews")
async def review_knowledge(artifact_id: str, request: KnowledgeReviewRequest) -> dict[str, Any]:
    try:
        return _store().review_knowledge(artifact_id, request.action, request.reviewer, request.note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="知识库不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/knowledge/artifacts/{artifact_id}/export")
async def export_knowledge(artifact_id: str) -> Response:
    try:
        content, media_type = _store().export_knowledge(artifact_id)
        return Response(content=content, media_type=media_type,
                        headers={"Content-Disposition": 'attachment; filename="knowledge.json"'})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="知识库不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/tickets")
async def create_ticket(request: TicketRequest) -> dict[str, Any]:
    try:
        return _store().create_ticket(request.customer_name, request.description, request.product, request.fault_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail=f"售后持久化依赖不可用：{exc}") from exc


@router.get("/tickets")
async def list_tickets(limit: int = 100) -> dict[str, Any]:
    try:
        return _store().list_tickets(limit)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail=f"售后持久化依赖不可用：{exc}") from exc


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str) -> dict[str, Any]:
    try:
        return _store().get_ticket(ticket_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="工单不存在") from exc


@router.post("/tickets/{ticket_id}/reviews")
async def review_ticket(ticket_id: str, request: TicketReviewRequest) -> dict[str, Any]:
    try:
        return _store().review_ticket(ticket_id, request.action, request.reviewer, request.engineer, request.note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="工单不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def answer_customer_consultation(text: str) -> dict[str, Any]:
    """Answer a customer question using the internal FAQ and intent routing."""
    return answer_consult(text)


def classify_customer_intent(text: str) -> dict[str, Any]:
    """Classify the intent of a real customer message with matched rules."""
    return classify_intent(text)


def build_and_review_service_knowledge(records: list[dict[str, Any]], title: str = "售后知识库") -> dict[str, Any]:
    """Extract, optimize and persist a reviewable knowledge artifact."""
    extracted = extract_knowledge(records)
    optimized = optimize_knowledge(extracted["entries"])
    return _store().create_knowledge_artifact(title, optimized["entries"])


def create_after_sale_ticket(customer_name: str, description: str, product: str = "", fault_type: str = "") -> dict[str, Any]:
    """Create a durable after-sale ticket with engineer routing awaiting review."""
    return _store().create_ticket(customer_name, description, product, fault_type)




# ==== 应用内默认智能体（真实模型对话，SSE 流式） ====
CONSOLE_CHAT_URL = "http://127.0.0.1:8088/api/console/chat"
CHAT_TIMEOUT_SECONDS = 300

APP_CONTEXT = (
    "你是「制造云 AI-OS」智能售后服务中心的智能助手。你可以调用 answer_customer_consultation、classify_customer_intent、create_after_sale_ticket、build_and_review_service_knowledge 等工具，"
    "基于用户工作台的真实业务数据回答问题；涉及分析结论时先调用对应工具再回答，不要凭空编造数据。"
)


class AgentChatRequest(BaseModel):
    """Client payload for the streaming in-app agent chat."""

    text: str = Field(min_length=1, max_length=4000, description="User message")
    session_id: str | None = Field(default=None, description="Persistent conversation id")
    user_id: str | None = Field(default="default", description="Calling user id")
    app_id: str | None = Field(default="zhiyun-service-studio", description="Owning app id")
    context: str | None = Field(default=None, description="Extra system context from the UI")
    history: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Prior turns [{role, text}] for multi-turn context",
    )


def _build_input(body: AgentChatRequest) -> list[dict[str, Any]]:
    """Build the console ``input`` message list from the dock payload."""
    context = APP_CONTEXT + ("\n" + body.context if body.context else "")
    input_messages: list[dict[str, Any]] = []
    if context:
        input_messages.append({"role": "system", "content": [{"type": "text", "text": context}]})
    for turn in body.history:
        if not isinstance(turn, dict):
            continue
        role = turn.get("role")
        text = turn.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        mapped_role = "assistant" if role in ("bot", "assistant") else "user"
        input_messages.append({"role": mapped_role, "content": [{"type": "text", "text": text}]})
    input_messages.append({"role": "user", "content": [{"type": "text", "text": body.text}]})
    return input_messages


@router.post("/agent/chat")
async def agent_chat(body: AgentChatRequest) -> StreamingResponse:
    """Proxy a user message to the real console chat and stream its SSE reply."""
    session_id = body.session_id or f"zhiyun-service-studio-{uuid4().hex}"
    payload = {
        "input": _build_input(body),
        "session_id": session_id,
        "user_id": body.user_id or "default",
        "stream": True,
        "metadata": {
            "app_id": body.app_id or "zhiyun-service-studio",
            "source_kind": "agent_dock",
            "data_mode": "real",
        },
    }

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async with httpx.AsyncClient(timeout=CHAT_TIMEOUT_SECONDS) as client:
                async with client.stream("POST", CONSOLE_CHAT_URL, json=payload) as response:
                    if response.status_code != 200:
                        err_body = await response.aread()
                        text = err_body.decode("utf-8", errors="replace")
                        yield f"data: {json.dumps({'error': text})}\n\n"
                        return
                    async for line in response.aiter_lines():
                        yield ("\n" if line == "" else line + "\n")
        except httpx.TimeoutException:
            yield f"data: {json.dumps({'error': '智能体响应超时，请稍后重试'})}\n\n"
        except Exception as exc:  # pragma: no cover - defensive
            yield f"data: {json.dumps({'error': f'调用智能体失败: {exc}'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


class ServiceStudioPlugin:
    def register(self, api: PluginApi) -> None:
        api.register_http_router(router, prefix="/zhiyun-service-studio", tags=["zhiyun-service-studio"])
        api.register_tool(
            tool_name="answer_customer_consultation",
            tool_func=answer_customer_consultation,
            description="根据客户咨询文本，从内置FAQ与意图规则生成应答；命中知识库时附历史维修依据，否则转人工。",
            icon="💬",
            tool_type="internal",
        )
        api.register_tool(
            tool_name="classify_customer_intent",
            tool_func=classify_customer_intent,
            description="识别客户咨询属于订单查询、售后报修、财务、退换货、投诉、产品或物流，并返回命中关键词与实体。",
            icon="🧠",
            tool_type="internal",
        )
        api.register_tool(
            tool_name="create_after_sale_ticket",
            tool_func=create_after_sale_ticket,
            description="基于真实故障描述创建售后工单，推荐处理团队和工程师并等待具名人员审阅；不会自动派单或执行。",
            icon="🎫",
            tool_type="internal",
        )
        api.register_tool(
            tool_name="build_and_review_service_knowledge",
            tool_func=build_and_review_service_knowledge,
            description="从真实维修记录提取故障知识、去重并打分，生成可审阅知识库；人工接受后可用作应答依据。",
            icon="📚",
            tool_type="internal",
        )


plugin = ServiceStudioPlugin()
