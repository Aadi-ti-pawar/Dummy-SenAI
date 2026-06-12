from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.models import Action, AuditLog, Contact, Email, Thread
from app.schemas.classification import AgentDecisionResponse
from app.services.knowledge_service import KnowledgeService


ACTION_BY_RECOMMENDATION = {
    "draft_reply": "Draft-Created",
    "escalate_to_human": "Escalate",
    "create_internal_ticket": "Ticket-Created",
    "flag_for_legal": "Legal-Flag",
    "manual_review": "Manual-Review",
}


class AgentToolbox:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.knowledge = KnowledgeService(db)

    def search_knowledge_base(self, query: str, top_k: int = 3) -> dict[str, Any]:
        return {"chunks": self.knowledge.search(query, top_k)}

    def get_thread_history(self, thread_pk: UUID, limit: int = 10) -> dict[str, Any]:
        emails = self.db.execute(
            select(Email)
            .where(Email.thread_id == thread_pk)
            .order_by(Email.timestamp.desc())
            .limit(limit)
        ).scalars()
        return {
            "emails": [
                {
                    "message_id": email.message_id,
                    "subject": email.subject,
                    "body": (email.body or "")[:400],
                    "category": email.category,
                    "sentiment": email.sentiment,
                    "urgency": email.urgency,
                    "timestamp": email.timestamp.isoformat(),
                }
                for email in emails
            ]
        }

    def get_contact_profile(self, sender_email: str) -> dict[str, Any]:
        contact = self.db.execute(select(Contact).where(Contact.email == sender_email)).scalar_one_or_none()
        if contact is None:
            return {"found": False, "email": sender_email}
        return {
            "found": True,
            "email": contact.email,
            "name": contact.name,
            "company": contact.company,
            "status": contact.status,
            "account_value": float(contact.account_value or 0),
            "churn_risk_score": float(contact.churn_risk_score or 0),
            "last_contact_at": contact.last_contact_at.isoformat() if contact.last_contact_at else None,
        }

    def check_account_status(self, sender_email: str) -> dict[str, Any]:
        profile = self.get_contact_profile(sender_email)
        if not profile.get("found"):
            return {"status": "unknown", "risk": "unknown"}
        risk_score = profile.get("churn_risk_score", 0)
        return {
            "status": profile.get("status"),
            "risk": "high" if risk_score >= 0.7 else "medium" if risk_score >= 0.4 else "low",
            "account_value": profile.get("account_value"),
        }

    def draft_reply(self, email: Email, citations: list[dict[str, Any]]) -> dict[str, Any]:
        citation_text = citations[0]["document"] if citations else "SenAI support policy"
        return {
            "draft": (
                f"Hi, thanks for reaching out about {email.subject or 'your request'}. "
                f"We reviewed the relevant guidance in {citation_text} and will follow up with the next step shortly."
            )
        }

    def escalate_to_human(self, reason: str) -> dict[str, Any]:
        return {"escalation": "pending", "reason": reason}

    def create_internal_ticket(self, email: Email, reason: str) -> dict[str, Any]:
        return {"ticket_key": f"SENAI-{str(email.id)[:8].upper()}", "reason": reason}

    def flag_for_legal(self, reason: str) -> dict[str, Any]:
        return {"legal_flag": "pending_review", "reason": reason}


class TriageAgentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.toolbox = AgentToolbox(db)
        self.reasoning_steps: list[dict[str, Any]] = []
        self.tool_calls = 0

    def run(self, email_id: UUID, dry_run: bool = False) -> AgentDecisionResponse:
        email = self.db.get(Email, email_id)
        if email is None:
            raise AppError(
                status_code=404,
                error_code="EMAIL_NOT_FOUND",
                message="Email was not found.",
                details={"email_id": str(email_id)},
            )

        self.reasoning_steps = []
        self.tool_calls = 0
        citations = []
        proposed_content = None

        if not self.settings.gemini_api_key:
            # Fallback to existing rule-based heuristic logic
            recommended, citations, proposed_content = self._run_heuristics(email)
        else:
            try:
                import google.generativeai as genai

                genai.configure(api_key=self.settings.gemini_api_key)
                model = genai.GenerativeModel(self.settings.gemini_model)

                recommended = None
                while self.tool_calls < self.settings.agent_max_tool_calls:
                    step_num = len(self.reasoning_steps) + 1
                    
                    # Format previous steps
                    formatted_steps = ""
                    for s in self.reasoning_steps:
                        formatted_steps += f"Step {s['step']}:\n"
                        formatted_steps += f"  Thought: {s['thought']}\n"
                        if s.get("action"):
                            formatted_steps += f"  Action: Call {s['action']['tool']} with params {json.dumps(s['action']['params'])}\n"
                        if s.get("observation"):
                            formatted_steps += f"  Observation: {json.dumps(s['observation'])}\n"
                        formatted_steps += "\n"
                    if not formatted_steps:
                        formatted_steps = "(None yet)\n"

                    prompt = f"""You are the SenAI CRM Triage Agent, an autonomous customer operations agent powered by a step-by-step reasoning and acting (ReAct) loop.
Your goal is to triage the following customer email and determine the best action. You have access to tools to gather more information, check client profiles, and search internal knowledge.

Email to triage:
- ID: {email.id}
- Sender: {email.sender}
- Subject: {email.subject or "(No Subject)"}
- Body: {email.body or "(Empty)"}
- Urgency: {email.urgency or "Unknown"}
- Category: {email.category or "Unknown"}
- Sentiment: {email.sentiment or "Neutral"}
- Sentiment Score: {email.sentiment_score or 0.0}

Triage Policies & Guidelines:
1. **Critical Urgency Safeguard**: Emails with "Critical" urgency MUST NEVER be auto-replied. You MUST make the final decision "escalate_to_human".
2. **GDPR/Data Privacy Requests**: If the email requests GDPR actions (e.g. data deletion, subject access request, DPA, privacy agreement, right to be forgotten), you MUST make the final decision "flag_for_legal".
3. **Ransomware / Security Alerts**: If the email contains security threats, ransomware demands, phishing warnings, or hacking reports, you MUST make the final decision "flag_for_legal" or "escalate_to_human".
4. **Billing/Refunds or Churn Risk**: If the email mentions billing issues, refund requests, or if the customer profile indicates high churn risk (churn risk score >= 0.7), you MUST make the final decision "create_internal_ticket" or "escalate_to_human".
5. **Technical Bug Reports**: If the email is a bug report or reports a technical problem, you MUST make the final decision "create_internal_ticket".
6. **General inquiries**: If the email is a general question (e.g., refund policy, product feature, base URL, login issues), you MUST search the knowledge base using `search_knowledge_base`. If relevant policy guidelines are found, you can make the final decision "draft_reply" using the retrieved documents. Otherwise, choose "escalate_to_human".

Available Tools:
- `get_contact_profile`: Retrieve CRM profile details for a sender. Params: {{"sender_email": "email_address"}}
- `check_account_status`: Check customer account status and churn risk. Params: {{"sender_email": "email_address"}}
- `get_thread_history`: Retrieve recent thread history. Params: {{"thread_pk": "thread_uuid_string", "limit": 10}}
- `search_knowledge_base`: Search the internal knowledge base for company policies, FAQs, and API documentation. Params: {{"query": "search_query", "top_k": 3}}

Your Output Format:
You MUST reply with a single, valid JSON object ONLY. Do not wrap it in anything else or add introductory/concluding text. The schema is:
{{
  "thought": "A detailed explanation of your current reasoning step.",
  "call_tool": "name_of_tool_to_call" or null,
  "tool_params": {{ ... arguments for the tool ... }} or null,
  "final_decision": "draft_reply" | "escalate_to_human" | "create_internal_ticket" | "flag_for_legal" | null
}}

Constraints:
- You must either call a tool or make a final decision. You cannot do both at once (if `call_tool` is not null, `final_decision` must be null, and vice versa).
- You can make up to {self.settings.agent_max_tool_calls} tool calls in total. If you exceed this limit without a final decision, the orchestrator will automatically escalate the request.
- Currently, you are on step {step_num} of {self.settings.agent_max_tool_calls}.

Here is the history of your steps so far:
{formatted_steps}

Reason step-by-step and decide what to do next.
"""
                    response = model.generate_content(
                        prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.0,
                            response_mime_type="application/json"
                        )
                    )
                    response_text = response.text.strip()
                    
                    # Parse JSON safely
                    start = response_text.find("{")
                    end = response_text.rfind("}") + 1
                    if start == -1 or end <= start:
                        raise ValueError(f"No JSON object found in response: {response_text}")
                    decision = json.loads(response_text[start:end])
                    
                    thought = decision.get("thought", "")
                    call_tool = decision.get("call_tool")
                    tool_params = decision.get("tool_params") or {}
                    final_decision = decision.get("final_decision")

                    if call_tool:
                        # Perform action
                        if self.tool_calls >= self.settings.agent_max_tool_calls:
                            observation = {"error": "max_tool_calls_reached"}
                        else:
                            self.tool_calls += 1
                            if call_tool == "get_contact_profile":
                                email_addr = tool_params.get("sender_email") or email.sender
                                observation = self.toolbox.get_contact_profile(email_addr)
                            elif call_tool == "check_account_status":
                                email_addr = tool_params.get("sender_email") or email.sender
                                observation = self.toolbox.check_account_status(email_addr)
                            elif call_tool == "get_thread_history":
                                thread_val = tool_params.get("thread_pk") or str(email.thread_id)
                                try:
                                    thread_uuid = UUID(thread_val)
                                except ValueError:
                                    thread_uuid = email.thread_id
                                limit_val = tool_params.get("limit") or 10
                                observation = self.toolbox.get_thread_history(thread_uuid, limit_val)
                            elif call_tool == "search_knowledge_base":
                                q = tool_params.get("query") or ""
                                top_k = tool_params.get("top_k") or 3
                                observation = self.toolbox.search_knowledge_base(q, top_k)
                                # Extract citations
                                new_citations = KnowledgeService.citations(observation.get("chunks", []))
                                for c in new_citations:
                                    if c not in citations:
                                        citations.append(c)
                            else:
                                observation = {"error": f"Unknown tool: {call_tool}"}

                        self.reasoning_steps.append({
                            "step": step_num,
                            "thought": thought,
                            "action": {"tool": call_tool, "params": tool_params},
                            "observation": observation
                        })
                    else:
                        if final_decision:
                            recommended = final_decision
                            self.reasoning_steps.append({
                                "step": step_num,
                                "thought": thought,
                                "action": None,
                                "observation": None
                            })
                            break
                        else:
                            # Neither tool nor final decision provided
                            recommended = "escalate_to_human"
                            self.reasoning_steps.append({
                                "step": step_num,
                                "thought": thought or "No tool call or final decision provided.",
                                "action": None,
                                "observation": None
                            })
                            break

                if not recommended:
                    recommended = "escalate_to_human"
                    self._thought("Max tool calls limit reached without final decision. Escalating to human.")

                # Enforce safeguards
                if email.urgency == "Critical" and recommended == "draft_reply":
                    recommended = "escalate_to_human"
                    self._thought("Enforced safeguard: Critical urgency email cannot be auto-replied. Escalating to human.")

                # Execute decision
                if recommended == "flag_for_legal":
                    decision_result = self.toolbox.flag_for_legal("Legal/compliance risk detected.")
                elif recommended == "create_internal_ticket":
                    decision_result = self.toolbox.create_internal_ticket(email, "Internal ticket created by ReAct Agent.")
                elif recommended == "escalate_to_human":
                    decision_result = self.toolbox.escalate_to_human(self._escalation_reason(email))
                else:
                    decision_result = self.toolbox.draft_reply(email, citations)
                    proposed_content = decision_result.get("draft")

            except Exception as e:
                import traceback
                print("EXC IN REACT LOOP:", e)
                traceback.print_exc()
                # Rollback current step / tool calls and do clean fallback to heuristics
                self.reasoning_steps = []
                self.tool_calls = 0
                citations = []
                proposed_content = None
                recommended, citations, proposed_content = self._run_heuristics(email)

        action_type = ACTION_BY_RECOMMENDATION.get(recommended, "Manual-Review")
        action_id = None
        created_at = None
        if not dry_run:
            action = self._persist_action(email, action_type, proposed_content, citations)
            action_id = action.id
            created_at = action.created_at
            self._audit(email, action)
            email.status = "Escalated" if action_type in {"Escalate", "Legal-Flag"} else "Processing"
            self.db.commit()

        return AgentDecisionResponse(
            email_id=email.id,
            action_id=action_id,
            action_type=action_type,
            recommended_action=recommended,
            confidence=0.92 if action_type != "Manual-Review" else 0.68,
            dry_run=dry_run,
            tool_calls_used=self.tool_calls,
            reasoning_steps=self.reasoning_steps,
            proposed_content=proposed_content,
            rag_citations=citations,
            created_at=created_at,
        )

    def _run_heuristics(self, email: Email) -> tuple[str, list[dict[str, Any]], str | None]:
        self._thought("Assess current classification, customer context, and policy guidance before selecting an action (Heuristic Fallback).")
        profile = self._act("get_contact_profile", {"sender_email": email.sender}, lambda: self.toolbox.get_contact_profile(email.sender))
        history = self._act("get_thread_history", {"thread_id": str(email.thread_id), "limit": 5}, lambda: self.toolbox.get_thread_history(email.thread_id, 5))
        account = self._act("check_account_status", {"sender_email": email.sender}, lambda: self.toolbox.check_account_status(email.sender))
        rag = self._act("search_knowledge_base", {"query": f"{email.category or ''} {email.subject or ''} {email.body or ''}", "top_k": 3}, lambda: self.toolbox.search_knowledge_base(f"{email.category or ''} {email.subject or ''} {email.body or ''}", 3))

        citations = KnowledgeService.citations(rag.get("chunks", []))
        recommended = self._decide(email, profile, history, account)
        proposed_content = None

        if self.tool_calls >= self.settings.agent_max_tool_calls and recommended == "draft_reply":
            recommended = "escalate_to_human"
            decision_result = self._act("escalate_to_human", {"reason": "Agent reached tool-call limit."}, lambda: self.toolbox.escalate_to_human("Agent reached tool-call limit."))
        elif recommended == "flag_for_legal":
            decision_result = self._act("flag_for_legal", {"reason": "Legal/compliance risk detected."}, lambda: self.toolbox.flag_for_legal("Legal/compliance risk detected."))
        elif recommended == "create_internal_ticket":
            decision_result = self._act("create_internal_ticket", {"reason": "Engineering or account follow-up required."}, lambda: self.toolbox.create_internal_ticket(email, "Engineering or account follow-up required."))
        elif recommended == "escalate_to_human":
            decision_result = self._act("escalate_to_human", {"reason": self._escalation_reason(email)}, lambda: self.toolbox.escalate_to_human(self._escalation_reason(email)))
        else:
            decision_result = self._act("draft_reply", {"email_id": str(email.id)}, lambda: self.toolbox.draft_reply(email, citations))
            proposed_content = decision_result.get("draft")

        return recommended, citations, proposed_content

    def _decide(self, email: Email, profile: dict[str, Any], history: dict[str, Any], account: dict[str, Any]) -> str:
        if email.urgency == "Critical":
            self._thought("Critical urgency cannot be auto-replied; route to a human owner.")
            return "escalate_to_human"
        if email.is_legal_threat or email.category in {"Legal", "Compliance"}:
            self._thought("Legal/compliance risk needs specialized review.")
            return "flag_for_legal"
        if email.requires_human or (email.confidence is not None and float(email.confidence) < 0.70):
            self._thought("Human review is required by confidence or classification flags.")
            return "escalate_to_human"
        if email.category in {"Bug Report", "Billing"} or account.get("risk") == "high":
            self._thought("Operational follow-up is needed; create an internal ticket.")
            return "create_internal_ticket"
        self._thought("No blocking risk detected; create a draft reply for approval.")
        return "draft_reply"

    def _act(self, action: str, params: dict[str, Any], callback: Any) -> dict[str, Any]:
        if self.tool_calls >= self.settings.agent_max_tool_calls:
            observation = {"error": "max_tool_calls_reached"}
        else:
            self.tool_calls += 1
            observation = callback()
        self.reasoning_steps.append(
            {
                "step": len(self.reasoning_steps) + 1,
                "thought": f"Use {action} to gather or perform the next required step.",
                "action": {"tool": action, "params": params},
                "observation": observation,
            }
        )
        return observation

    def _thought(self, thought: str) -> None:
        self.reasoning_steps.append(
            {
                "step": len(self.reasoning_steps) + 1,
                "thought": thought,
                "action": None,
                "observation": None,
            }
        )

    def _persist_action(
        self,
        email: Email,
        action_type: str,
        proposed_content: str | None,
        citations: list[dict[str, Any]],
    ) -> Action:
        action = Action(
            email_id=email.id,
            thread_id=email.thread_id,
            agent_reasoning_log=self.reasoning_steps,
            agent_model="senai-react-agent",
            reasoning_trace=json.dumps(self.reasoning_steps, default=str),
            action_type=action_type,
            proposed_content=proposed_content,
            execution_status="Pending",
            rag_citations=citations,
        )
        self.db.add(action)
        self.db.flush()
        return action

    def _audit(self, email: Email, action: Action) -> None:
        self.db.add(
            AuditLog(
                entity_type="action",
                entity_id=action.id,
                action="AGENT_DECISION_CREATED",
                performed_by="triage_agent",
                old_values={},
                new_values={
                    "email_id": str(email.id),
                    "action_type": action.action_type,
                    "tool_calls": self.tool_calls,
                },
            )
        )

    @staticmethod
    def _escalation_reason(email: Email) -> str:
        entities = email.raw_entities or {}
        return (
            entities.get("classification", {}).get("escalation_reason")
            or "Human review required by urgency, confidence, or policy."
        )
