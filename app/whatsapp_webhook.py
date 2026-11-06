"""WhatsApp Cloud API webhook: verification handshake + inbound message intake.

Public routes (no login): Meta must be able to reach them. Security comes from the
verify token (handshake) and the HMAC signature on every POST.
"""
from __future__ import annotations

import json
import logging
import os

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
    return os.getenv("EAAaZAbstuKpcBS2ZC13PbRqOSbhPkU09lO6dK8NfihVeEZAyQlKVNcckHhPffn60ZC2M6z1DNUIBQDRG4IZBwQKdenQUi4ZCudVGml9kgCCBMB7ix6yNGJhK1RRZCMVpfvMCZCtpjmAXkVHfs96P7ZCLf2MNwN2dZCBHkfxiAwJkwr9m0aF2dqApZBztaZC9VNhG2QNhTcbzcIDA6ftwANu4HLUnWJEpeWgyG3dR1tgZCyR4wcjMzYkNbaBS80iF6hURwD2iaM5MmUWZCFZA17UDG0YRWxAvOMv", "")


def _app_secret() -> str:
    return os.getenv("c65d4d1bbac3552e190cb52e5a7067050673d50ff01c2497", "")


@router.get("")
def verify(request: Request):
    """Meta's one-time handshake when you click 'Verify and save'."""
    q = request.query_params
    token = _verify_token()
    if token and q.get("hub.mode") == "subscribe" and q.get("hub.verify_token") == token:
        return PlainTextResponse(q.get("hub.challenge", ""))
    raise HTTPException(status_code=403, detail="Verification failed")


def _direct_inbox(db: Session) -> BrokerGroup:
    group = db.query(BrokerGroup).filter(BrokerGroup.name == DIRECT_INBOX_NAME).first()
    if not group:
        group = BrokerGroup(name=DIRECT_INBOX_NAME, platform="whatsapp", sort_order=99,
                            notes="Posts sent or forwarded directly to the DA'PLUG WhatsApp number.")
        db.add(group)
        db.flush()
    return group


@router.post("")
async def receive(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    if not verify_signature(body, request.headers.get("X-Hub-Signature-256"), _app_secret()):
        raise HTTPException(status_code=403, detail="Invalid signature")
    try:
        payload = json.loads(body)
    except ValueError:
        return Response(status_code=200)  # malformed: ack so Meta does not retry forever

    # Imported lazily: main.py owns the extraction/matching pipeline.
    from .main import create_broker_post

    for msg in extract_messages(payload):
        wamid = msg["wamid"]
        if not wamid or db.query(RawMessage).filter(RawMessage.provider_message_id == wamid).first():
            continue  # Meta retries deliveries; never store the same message twice
        raw = RawMessage(
            provider="whatsapp_cloud", provider_message_id=wamid,
            from_phone=msg["from_phone"], sender_name=msg["sender_name"],
            msg_type=msg["msg_type"], text=msg["text"], media_id=msg["media_id"],
            mime_type=msg["mime_type"], filename=msg["filename"],
            received_at=msg["received_at"], payload=msg["raw"], status="received",
        )
        db.add(raw)
        db.flush()
        try:
            if msg["text"] and msg["text"].strip():
                group = _direct_inbox(db)
                post, _dup = create_broker_post(
                    db, group_id=group.id, raw_text=msg["text"],
                    sender_name=msg["sender_name"], sender_phone=msg["from_phone"],
                    source_type="whatsapp_cloud", external_message_id=wamid,
                    received_at=msg["received_at"],
                )
                raw.broker_post_id = post.id
                raw.status = "processed"
            else:
                raw.status = "stored_media_only" if msg["media_id"] else "ignored"
        except Exception:  # never let one bad message break the batch or trigger Meta retries
            log.exception("Failed to process WhatsApp message %s", wamid)
            raw.status = "error"
        db.commit()
    return Response(status_code=200)
