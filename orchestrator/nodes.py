"""Activation node utilities for orchestrated workflows.

Each function is intentionally simple and side-effect free so that
LLM-generated workflow scripts can import and reuse them safely.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class Message:
    """Represents a message sent through a channel."""

    recipient: str
    body: str
    channel: str = "chat"

    def serialize(self) -> Dict[str, str]:
        """Serialize the message for logging or downstream processing."""
        return {"recipient": self.recipient, "body": self.body, "channel": self.channel}


def send_message(recipient: str, body: str, channel: str = "chat") -> Message:
    """Send a short chat-style message.

    Args:
        recipient: Name or handle that should receive the message.
        body: The full message contents.
        channel: A hint for the delivery mechanism (e.g., "sms", "slack", "chat").
    """

    message = Message(recipient=recipient, body=body, channel=channel)
    return message


def send_email(
    to: Iterable[str],
    subject: str,
    body: str,
    *,
    cc: Optional[Iterable[str]] = None,
    bcc: Optional[Iterable[str]] = None,
    attachments: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compose an email payload.

    Args:
        to: One or more primary recipients.
        subject: Email subject line.
        body: Main email body.
        cc: Optional list of recipients to copy.
        bcc: Optional list of recipients to blind copy.
        attachments: Optional list of file paths or descriptors.
    """

    payload: Dict[str, Any] = {
        "to": list(to),
        "subject": subject,
        "body": body,
        "cc": list(cc) if cc else [],
        "bcc": list(bcc) if bcc else [],
        "attachments": attachments or [],
    }
    return payload


def draft_email(subject: str, to: Iterable[str], key_points: List[str]) -> str:
    """Draft a concise email from key points."""

    bullets = "\n".join(f"- {point}" for point in key_points)
    email_body = f"Subject: {subject}\nTo: {', '.join(to)}\n\nKey points:\n{bullets}"
    return email_body


def make_call(phone_number: str, script: str) -> Dict[str, str]:
    """Prepare instructions for a phone call."""

    return {"number": phone_number, "script": script}


def generate_summary(text: str, style: str = "concise") -> str:
    """Generate a lightweight summary stub.

    This function is intentionally non-AI to keep the module dependency-free.
    """

    preview = text.strip().split("\n", maxsplit=1)[0][:160]
    return f"[{style} summary] {preview}..."


def web_search(query: str, *, top_k: int = 3) -> Dict[str, Any]:
    """Represent a web search request."""

    return {"type": "web_search", "query": query, "top_k": top_k}


def doc_search(query: str, source: str, *, top_k: int = 3) -> Dict[str, Any]:
    """Represent a documentation search request."""

    return {"type": "doc_search", "query": query, "source": source, "top_k": top_k}


def fetch_calendar_events(date: str) -> Dict[str, Any]:
    """Example utility: fetch events for a date from a calendar system."""

    return {"type": "calendar_lookup", "date": date}
