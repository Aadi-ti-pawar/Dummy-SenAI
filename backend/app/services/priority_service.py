import re
from dataclasses import dataclass, field

INTERNAL_DOMAINS = {"internal.com", "mycompany.com"}
SPAM_DOMAINS = {"marketing-guru.io"}

SPAM_KEYWORDS = {
    "boost your seo",
    "front page of google",
    "limited offer",
    "click here",
    "nigerian prince",
    "inheritance",
    "wire transfer",
    "cold outreach",
}

URGENT_KEYWORDS = {
    "urgent",
    "p0",
    "critical",
    "emergency",
    "immediately",
    "asap",
    "production down",
    "system down",
    "outage",
}

SECURITY_KEYWORDS = {
    "ransomware",
    "send 2 btc",
    "publish data",
    "suspicious login",
    "unauthorized access",
    "data breach",
    "breach",
    "compromised",
    "malware",
}

LEGAL_KEYWORDS = {
    "legal",
    "cease and desist",
    "lawsuit",
    "formal correspondence",
    "gdpr",
    "article 20",
    "data portability",
    "hipaa",
    "dpa",
}

COMPLAINT_KEYWORDS = {"unhappy", "angry", "terrible", "worst", "refund", "missed", "escalating"}
BUG_KEYWORDS = {"bug", "error", "403", "crash", "broken", "corruption", "data missing"}
BILLING_KEYWORDS = {"billing", "invoice", "refund", "credit", "pro-rata", "subscription"}
FEATURE_KEYWORDS = {"feature request", "would like", "can you add", "support for"}

ORDER_RE = re.compile(r"(?:order\s*#?\s*)([A-Za-z0-9_-]+)", re.IGNORECASE)
TICKET_RE = re.compile(r"(?:ticket\s*#?\s*)([A-Za-z0-9_-]+)", re.IGNORECASE)
MONEY_RE = re.compile(r"\$[\d,]+(?:\.\d{2})?")
DEADLINE_RE = re.compile(r"\b(?:\d+\s?(?:hours?|days?)|within 24 hours|by [A-Z][a-z]+day|deadline)\b", re.IGNORECASE)


@dataclass(frozen=True)
class HeuristicResult:
    category: str
    urgency: str
    priority_score: int
    confidence: float
    requires_human: bool
    is_internal: bool = False
    is_spam: bool = False
    is_security_alert: bool = False
    is_legal_threat: bool = False
    reasons: list[str] = field(default_factory=list)
    entities: dict[str, list[str]] = field(default_factory=dict)


def _contains_any(text: str, keywords: set[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword in text]


def _sender_domain(sender: str) -> str:
    return sender.rsplit("@", 1)[-1].lower()


def _score_to_urgency(score: int) -> str:
    if score >= 90:
        return "Critical"
    if score >= 70:
        return "High"
    if score >= 35:
        return "Medium"
    return "Low"


def _category_from_keywords(text: str, is_spam: bool, is_internal: bool, legal_hits: list[str]) -> str:
    if is_spam:
        return "Spam"
    if is_internal:
        return "Internal"
    if legal_hits:
        if any(hit in {"gdpr", "article 20", "data portability", "hipaa", "dpa"} for hit in legal_hits):
            return "Compliance"
        return "Legal"
    if _contains_any(text, BUG_KEYWORDS):
        return "Bug Report"
    if _contains_any(text, BILLING_KEYWORDS):
        return "Billing"
    if _contains_any(text, FEATURE_KEYWORDS):
        return "Feature Request"
    if _contains_any(text, COMPLAINT_KEYWORDS):
        return "Complaint"
    return "Inquiry"


def extract_entities(text: str) -> dict[str, list[str]]:
    return {
        "order_ids": sorted(set(ORDER_RE.findall(text))),
        "ticket_ids": sorted(set(TICKET_RE.findall(text))),
        "monetary_amounts": sorted(set(MONEY_RE.findall(text))),
        "deadlines": sorted(set(DEADLINE_RE.findall(text))),
        "products_mentioned": [],
    }


def score_email(sender: str, subject: str, body: str) -> HeuristicResult:
    domain = _sender_domain(sender)
    text = f"{subject} {body}".lower()

    spam_hits = _contains_any(text, SPAM_KEYWORDS)
    urgent_hits = _contains_any(text, URGENT_KEYWORDS)
    security_hits = _contains_any(text, SECURITY_KEYWORDS)
    legal_hits = _contains_any(text, LEGAL_KEYWORDS)
    complaint_hits = _contains_any(text, COMPLAINT_KEYWORDS)

    is_internal = domain in INTERNAL_DOMAINS
    is_spam = domain in SPAM_DOMAINS or bool(spam_hits)
    is_security_alert = bool(security_hits)
    is_legal_threat = bool(legal_hits)

    score = 20
    reasons: list[str] = []

    if is_spam:
        score = 5
        reasons.append("spam_signal")
    if is_internal:
        score = max(score, 15)
        reasons.append("internal_sender")
    if urgent_hits:
        score += 35
        reasons.extend(f"urgent:{hit}" for hit in urgent_hits)
    if complaint_hits:
        score += 20
        reasons.extend(f"complaint:{hit}" for hit in complaint_hits)
    if legal_hits:
        score += 45
        reasons.extend(f"legal:{hit}" for hit in legal_hits)
    if security_hits:
        score += 60
        reasons.extend(f"security:{hit}" for hit in security_hits)

    if is_spam:
        urgency = "Low"
        requires_human = False
    else:
        score = min(score, 100)
        urgency = _score_to_urgency(score)
        requires_human = urgency == "Critical" or is_security_alert or is_legal_threat

    category = _category_from_keywords(text, is_spam, is_internal, legal_hits)

    return HeuristicResult(
        category=category,
        urgency=urgency,
        priority_score=score,
        confidence=0.75 if not is_spam else 0.85,
        requires_human=requires_human,
        is_internal=is_internal,
        is_spam=is_spam,
        is_security_alert=is_security_alert,
        is_legal_threat=is_legal_threat,
        reasons=reasons or ["default_priority"],
        entities=extract_entities(f"{subject} {body}"),
    )


def higher_priority(left: str, right: str) -> str:
    order = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
    return left if order.get(left, 0) >= order.get(right, 0) else right
