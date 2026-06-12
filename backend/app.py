"""FastAPI entry point for the SenAI CRM intelligence backend."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from backend.config import settings
from backend.db import dict_cursor
from backend.processor import process_existing_email
from scripts.gemini_classifier import classify_email_with_gemini
from scripts.langgraph_agent import ReasoningAgent


app = FastAPI(title="SenAI CRM Intelligence API", version="0.1.0")


class EmailPayload(BaseModel):
    message_id: str | None = None
    sender: str
    subject: str = ""
    body: str
    timestamp: str | None = None
    category: str | None = None
    urgency: str | None = None
    sentiment: str | None = None


class ProcessResponse(BaseModel):
    message_id: str
    classification: Dict[str, Any]
    agent: Dict[str, Any]
    action_id: str
    action_type: str


@app.get("/health")
def health() -> Dict[str, Any]:
    db_ok = False
    try:
        with dict_cursor() as (_, cur):
            cur.execute("SELECT 1 AS ok")
            db_ok = cur.fetchone()["ok"] == 1
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
        "gemini_configured": bool(settings.gemini_api_key),
    }


@app.get("/emails/review")
def emails_requiring_review(limit: int = Query(default=25, ge=1, le=100)) -> List[Dict[str, Any]]:
    with dict_cursor() as (_, cur):
        cur.execute(
            """
            SELECT message_id, sender, subject, category, urgency, sentiment,
                   confidence, requires_human, status, created_at
            FROM emails
            WHERE requires_human = TRUE
               OR urgency IN ('Critical', 'High')
               OR is_security_alert = TRUE
               OR is_legal_threat = TRUE
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


@app.post("/emails/{message_id}/process", response_model=ProcessResponse)
def process_email(message_id: str) -> Dict[str, Any]:
    try:
        return process_existing_email(message_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/classify")
def classify_email(payload: EmailPayload) -> Dict[str, Any]:
    result = classify_email_with_gemini(_payload_dict(payload))
    if not result["success"]:
        raise HTTPException(status_code=502, detail=result["error"])
    return result["classification"]


@app.post("/agent/reason")
def reason_about_email(payload: EmailPayload) -> Dict[str, Any]:
    return ReasoningAgent().reason_about_email(_payload_dict(payload))


def _payload_dict(payload: BaseModel) -> Dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()
