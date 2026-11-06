"""Pure helpers for the WhatsApp Cloud API webhook (stdlib only, easy to test)."""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any


def verify_signature(body: bytes, header: str | None, app_secret: str | None) -> bool:
    """Check Meta's X-Hub-Signature-256 header. Fails closed if no secret is set."""
    if not app_secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header[len("sha256="):])


def extract_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten a Cloud API webhook payload into simple message dicts.

    Status-only callbacks (sent/delivered/read) produce no messages.
    """
    out: list[dict[str, Any]] = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            if change.get("field") != "messages":
                continue
            value = change.get("value") or {}
            names = {c.get("wa_id"): (c.get("profile") or {}).get("name")
                     for c in value.get("contacts") or []}
            for m in value.get("messages") or []:
                mtype = m.get("type") or "unknown"
                body = m.get(mtype) if isinstance(m.get(mtype), dict) else {}
                text = None
                media_id = None
                mime = None
                filename = None
                if mtype == "text":
                    text = body.get("body")
                elif mtype in ("image", "video", "document", "audio"):
                    text = body.get("caption")
                    media_id = body.get("id")
                    mime = body.get("mime_type")
                    filename = body.get("filename")
                elif mtype == "button":
                    text = (m.get("button") or {}).get("text")
                ts = m.get("timestamp")
                try:
                    received = datetime.fromtimestamp(int(ts), tz=timezone.utc) if ts else None
                except (TypeError, ValueError, OSError):
                    received = None
                sender = m.get("from")
                out.append({
                    "wamid": m.get("id"),
                    "from_phone": sender,
                    "sender_name": names.get(sender),
                    "msg_type": mtype,
                    "text": text,
                    "media_id": media_id,
                    "mime_type": mime,
                    "filename": filename,
                    "received_at": received,
                    "raw": m,
                })
    return out
