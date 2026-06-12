import html
import re
from dataclasses import dataclass

from app.core.config import get_settings

TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class NormalizedEmailText:
    subject: str
    body: str
    processing_body: str
    warnings: list[str]
    original_body_length: int


def normalize_text(value: str) -> str:
    unescaped = html.unescape(value or "")
    without_tags = TAG_RE.sub(" ", unescaped)
    return WHITESPACE_RE.sub(" ", without_tags).strip()


def normalize_email_text(subject: str, body: str) -> NormalizedEmailText:
    settings = get_settings()
    warnings: list[str] = []

    normalized_subject = normalize_text(subject)
    normalized_body = normalize_text(body)

    if not normalized_subject:
        warnings.append("EMPTY_SUBJECT")
    if not normalized_body:
        warnings.append("EMPTY_BODY")

    processing_body = normalized_body
    if len(processing_body) > settings.email_processing_body_limit:
        processing_body = processing_body[: settings.email_processing_body_limit]
        warnings.append("BODY_TRUNCATED_FOR_PROCESSING")

    return NormalizedEmailText(
        subject=normalized_subject,
        body=normalized_body,
        processing_body=processing_body,
        warnings=warnings,
        original_body_length=len(body or ""),
    )
