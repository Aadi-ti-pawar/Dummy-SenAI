"""End-to-end email processing orchestration."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict

from psycopg2.extras import Json

from backend.db import dict_cursor
from scripts.gemini_classifier import classify_email_with_gemini
from scripts.langgraph_agent import ReasoningAgent


ACTION_BY_RECOMMENDATION = {
    "escalate_to_human": "Escalate",
    "draft_reply": "Draft-Created",
}


def _requires_human(classification: Dict[str, Any]) -> bool:
    return any(
        [
            classification.get("confidence", 1) < 0.70,
            classification.get("urgency") == "Critical",
            classification.get("is_security_alert"),
            classification.get("is_legal_threat"),
            classification.get("is_gdpr_request"),
        ]
    )


def get_email_by_message_id(message_id: str) -> Dict[str, Any] | None:
    with dict_cursor() as (_, cur):
        cur.execute(
            """
            SELECT e.*, t.thread_id AS external_thread_id
            FROM emails e
            JOIN threads t ON t.id = e.thread_id
            WHERE e.message_id = %s
            """,
            (message_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def process_existing_email(message_id: str) -> Dict[str, Any]:
    email = get_email_by_message_id(message_id)
    if not email:
        raise ValueError(f"Email not found for message_id={message_id}")

    email_payload = {
        "message_id": email["message_id"],
        "sender": email["sender"],
        "subject": email["subject"],
        "body": email["body"],
        "timestamp": email["timestamp"].isoformat() if email.get("timestamp") else None,
    }

    classification_result = classify_email_with_gemini(email_payload)
    if not classification_result["success"]:
        raise RuntimeError(classification_result["error"])

    classification = classification_result["classification"]
    with dict_cursor() as (_, cur):
        cur.execute(
            """
            UPDATE emails
            SET category = %s,
                urgency = %s,
                sentiment = %s,
                sentiment_score = %s,
                confidence = %s,
                requires_human = %s,
                is_spam = %s,
                is_security_alert = %s,
                is_legal_threat = %s,
                raw_entities = COALESCE(raw_entities, '{}'::jsonb) || %s::jsonb,
                status = 'Processing',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (
                classification.get("category"),
                classification.get("urgency"),
                classification.get("sentiment"),
                classification.get("sentiment_score"),
                classification.get("confidence"),
                _requires_human(classification),
                classification.get("is_spam", False),
                classification.get("is_security_alert", False),
                classification.get("is_legal_threat", False),
                json.dumps({"gemini_reasoning": classification.get("reasoning")}),
                email["id"],
            ),
        )

    agent_input = {**email_payload, **classification}
    agent_result = ReasoningAgent().reason_about_email(agent_input)
    action_type = ACTION_BY_RECOMMENDATION.get(
        agent_result["recommended_action"],
        "Manual-Review",
    )
    proposed_content = _extract_proposed_content(agent_result)

    with dict_cursor() as (_, cur):
        cur.execute(
            """
            INSERT INTO actions (
                email_id,
                thread_id,
                agent_reasoning_log,
                agent_model,
                reasoning_trace,
                action_type,
                proposed_content,
                execution_status,
                rag_citations,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pending', %s, %s, %s)
            RETURNING id
            """,
            (
                email["id"],
                email["thread_id"],
                Json(agent_result["reasoning_steps"]),
                "langgraph-react",
                json.dumps(agent_result["reasoning_steps"], default=str),
                action_type,
                proposed_content,
                Json(_extract_rag_citations(agent_result)),
                datetime.utcnow(),
                datetime.utcnow(),
            ),
        )
        action_id = cur.fetchone()["id"]
        cur.execute(
            "UPDATE emails SET status = %s WHERE id = %s",
            ("Escalated" if action_type == "Escalate" else "Replied", email["id"]),
        )

    return {
        "message_id": message_id,
        "classification": classification,
        "agent": agent_result,
        "action_id": str(action_id),
        "action_type": action_type,
    }


def _extract_proposed_content(agent_result: Dict[str, Any]) -> str | None:
    for step in reversed(agent_result.get("reasoning_steps", [])):
        observation = step.get("observation") or {}
        result = observation.get("result") if isinstance(observation, dict) else None
        if isinstance(result, dict) and "draft" in result:
            return result["draft"]
    return None


def _extract_rag_citations(agent_result: Dict[str, Any]) -> list:
    citations = []
    for step in agent_result.get("reasoning_steps", []):
        observation = step.get("observation") or {}
        if observation.get("tool") != "search_knowledge_base":
            continue
        for item in observation.get("result", []):
            if "error" not in item:
                citations.append(
                    {
                        "document": item.get("document"),
                        "section": item.get("section"),
                        "similarity": item.get("similarity"),
                    }
                )
    return citations
