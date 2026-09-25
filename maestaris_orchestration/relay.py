from __future__ import annotations

import json
import re
from typing import Any

from .protocol import protocol_fields, validate_protocol_comment

_EVENT_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,180}$")
_ALLOWED_PREFIXES = (
    "[WORKER:",
    "[ORCHESTRATOR-CLAIM:v1]",
    "[ORCHESTRATOR-REVIEW:v1]",
)


def validate_relay_request(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != 1:
        errors.append("relay schema must be 1")

    event_id = str(payload.get("event_id") or "")
    if not _EVENT_ID_RE.fullmatch(event_id):
        errors.append("relay event_id must match [A-Za-z0-9._:-]{1,180}")

    issue_number = payload.get("issue_number")
    if not isinstance(issue_number, int) or issue_number <= 0:
        errors.append("relay issue_number must be a positive integer")

    body = payload.get("body")
    if not isinstance(body, str) or not body.strip():
        errors.append("relay body must be a non-empty string")
        return errors
    if len(body) > 30000:
        errors.append("relay body exceeds 30000 characters")
    if not body.lstrip().startswith(_ALLOWED_PREFIXES):
        errors.append("relay body must be a canonical Maestaris worker/review protocol event")

    fields = protocol_fields(body)
    if fields.get("relay_event_id") != event_id:
        errors.append("relay body relay_event_id must equal event_id")

    errors.extend(validate_protocol_comment(body))
    return errors


def parse_relay_request(raw: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("relay request must be a JSON object")
    errors = validate_relay_request(payload)
    if errors:
        raise ValueError("; ".join(errors))
    return payload


def comment_has_event_id(body: str, event_id: str) -> bool:
    return protocol_fields(body or "").get("relay_event_id") == event_id
