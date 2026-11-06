"""WhatsApp Cloud API webhook: verification handshake + inbound message intake.

Public routes (no login): Meta must be able to reach them. Security comes from the
verify token (handshake) and the HMAC signature on every POST.
"""
from __future__ import annotations

import json
import logging
import os
import hmac
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from .database import get_db
from .models import BrokerGroup, RawMessage
from .whatsapp_parse import extract_messages, verify_signature

log = logging.getLogger("daplug.whatsapp")
router = APIRouter(prefix="/webhooks/whatsapp", tags=["whatsapp"])

DIRECT_INBOX_NAME = "DA'PLUG Direct Inbox"


def _verify_token() -> str:
    return os.getenv("WHATSAPP_VERIFY_TOKEN", "6CDxcRmX7aFQXEjTyhC2Vkk8wU1J79A6rWyGnHc-ODw").strip()


def _app_secret() -> str:
    return os.getenv("META_APP_SECRET", "56bf52a1453e05fd309ca14645406370").strip()


@router.get("")
def verify(request: Request):
    """Meta WhatsApp webhook verification handshake."""

    q = request.query_params

    token = _verify_token()
    supplied_token = q.get("hub.verify_token", "")
    mode = q.get("hub.mode", "")
    challenge = q.get("hub.challenge", "")

    if not token:
        log.error("WhatsApp webhook: WHATSAPP_VERIFY_TOKEN is missing")
        raise HTTPException(status_code=500, detail="Verify token not configured")

    if mode != "subscribe":
        log.warning("WhatsApp webhook: Invalid verification mode")
        raise HTTPException(status_code=403, detail="Invalid mode")

    if not hmac.compare_digest(supplied_token, token):
        log.warning("WhatsApp webhook: Verify token mismatch")
        raise HTTPException(status_code=403, detail="Invalid verify token")

    log.info("WhatsApp webhook verification successful")

    return PlainTextResponse(challenge)