from __future__ import annotations

import csv
import io
import re
import hashlib
import uuid
import zipfile
import mimetypes
from types import SimpleNamespace
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request, Response, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_

from .database import Base, engine, get_db, DATA_DIR
from .models import User, Contact, Lead, Requirement, Property, Match, Task, Activity, AuditLog, BrokerGroup, BrokerPost, BrokerFeedMatch
from .schemas import SetupIn, LoginIn, LeadIn, LeadUpdate, PropertyIn, PropertyUpdate, TaskIn, TaskUpdate, UserIn, BrokerPostIn, BrokerGroupUpdate, BrokerFeedMatchUpdate
from .security import hash_password, verify_password, create_session, read_session
from .matching import refresh_matches, refresh_matches_for_property, calculate_match
from .broker_feed import parse_broker_post, split_whatsapp_export, classify_broker_message, split_property_entries
from .local_ocr import extract_text_by_media

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
COOKIE_NAME = "property_os_session"

app = FastAPI(title="Property OS V2", version="2.1.3", docs_url="/api/docs", redoc_url=None)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

from .whatsapp_webhook import router as whatsapp_router  # noqa: E402
app.include_router(whatsapp_router)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = read_session(request.cookies.get(COOKIE_NAME))
    if not user_id:
        raise HTTPException(status_code=401, detail="Please sign in")
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Session is no longer valid")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


def clean_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    return re.sub(r"[^0-9+]", "", phone.strip()) or None


def log_activity(db: Session, user_id: int, entity_type: str, entity_id: int, action: str, summary: str):
    db.add(AuditLog(user_id=user_id, entity_type=entity_type, entity_id=entity_id, action=action, summary=summary))


def lead_payload(lead: Lead):
    req = lead.requirement
    return {
        "id": lead.id, "lead_code": lead.lead_code, "name": lead.contact.name,
        "phone": lead.contact.phone, "email": lead.contact.email, "company": lead.contact.company,
        "lead_type": lead.lead_type, "status": lead.status, "priority": lead.priority,
        "source": lead.source, "assigned_to": lead.assigned_to,
        "assigned_name": lead.assignee.full_name if lead.assignee else None,
        "notes": lead.notes, "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
        "requirement": ({
            "id": req.id, "transaction_type": req.transaction_type, "category": req.category,
            "property_type": req.property_type, "city": req.city,
            "preferred_locations": req.preferred_locations or [],
            "min_budget": float(req.min_budget) if req.min_budget is not None else None,
            "max_budget": float(req.max_budget) if req.max_budget is not None else None,
            "stretch_budget": float(req.stretch_budget) if req.stretch_budget is not None else None,
            "configuration": req.configuration,
            "min_area_sqft": float(req.min_area_sqft) if req.min_area_sqft is not None else None,
            "max_area_sqft": float(req.max_area_sqft) if req.max_area_sqft is not None else None,
            "furnishing": req.furnishing, "parking_required": req.parking_required,
            "amenities": req.amenities or [], "strict_location": req.strict_location,
            "strict_configuration": req.strict_configuration, "move_timeline": req.move_timeline,
            "notes": req.notes,
        } if req else None)
    }


def property_payload(p: Property):
    return {
        "id": p.id, "property_code": p.property_code, "title": p.title,
        "transaction_type": p.transaction_type, "category": p.category, "property_type": p.property_type,
        "city": p.city, "locality": p.locality, "address": p.address, "price": float(p.price),
        "bhk": p.bhk, "area_sqft": float(p.area_sqft) if p.area_sqft is not None else None,
        "furnishing": p.furnishing, "floor": p.floor, "parking": p.parking,
        "amenities": p.amenities or [], "status": p.status, "source_type": p.source_type,
        "owner_contact_id": p.owner_contact_id, "source_contact_id": p.source_contact_id,
        "asking_commission": float(p.asking_commission) if p.asking_commission is not None else None,
        "verified_at": p.verified_at.isoformat() if p.verified_at else None,
        "notes": p.notes, "assigned_to": p.assigned_to,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }



DEFAULT_BROKER_GROUPS = [f"Broker Group {i}" for i in range(1, 6)]


def ensure_broker_groups(db: Session):
    if db.query(BrokerGroup).count() == 0:
        for i, name in enumerate(DEFAULT_BROKER_GROUPS, start=1):
            db.add(BrokerGroup(name=name, platform="whatsapp", sort_order=i,
                               notes="Rename this placeholder to the actual WhatsApp group name."))
        db.flush()


def parse_export_datetime(date_text: str, time_text: str) -> datetime | None:
    date_value = None
    for fmt in ("%d/%m/%y", "%d/%m/%Y", "%m/%d/%y", "%m/%d/%Y"):
        try:
            date_value = datetime.strptime(date_text, fmt).date()
            break
        except ValueError:
            continue
    if not date_value:
        return None
    time_value = None
    normalized_time = re.sub(r"\s+", " ", (time_text or "").replace("\u202f", " ").replace("\u00a0", " ")).strip().upper()
    for fmt in ("%I:%M:%S %p", "%I:%M %p", "%H:%M:%S", "%H:%M"):
        try:
            time_value = datetime.strptime(normalized_time, fmt).time()
            break
        except ValueError:
            continue
    if not time_value:
        return None
    return datetime.combine(date_value, time_value)


def broker_post_candidate(parsed: dict):
    """A transient Property-like object; raw broker posts are not inventory yet."""
    return SimpleNamespace(
        status="available",
        transaction_type=parsed.get("transaction_type"),
        category=parsed.get("category"),
        property_type=parsed.get("property_type"),
        locality=parsed.get("locality"),
        city=parsed.get("city"),
        price=parsed.get("price"),
        bhk=parsed.get("configuration"),
        area_sqft=parsed.get("area_sqft"),
        furnishing=parsed.get("furnishing"),
        parking=parsed.get("parking"),
        amenities=parsed.get("amenities") or [],
    )


def upsert_broker_feed_match(db: Session, post: BrokerPost, req: Requirement) -> BrokerFeedMatch | None:
    """Score one broker candidate against one client requirement and retain review state."""
    parsed = post.parsed_data or {}
    if parsed.get("transaction_type") not in {"sale", "rent"}:
        return None
    evidence_keys = ("category", "property_type", "locality", "price", "configuration", "area_sqft")
    if not any(parsed.get(key) not in (None, "", []) for key in evidence_keys):
        return None
    result = calculate_match(req, broker_post_candidate(parsed))
    existing = db.query(BrokerFeedMatch).filter_by(
        broker_post_id=post.id, requirement_id=req.id
    ).first()
    if result is None:
        if existing and existing.status in {"new", "shortlisted"}:
            existing.status = "stale"
        return None
    score, reasons = result
    if existing is None:
        existing = BrokerFeedMatch(
            broker_post_id=post.id, requirement_id=req.id,
            score=score, reasons=reasons, status="new"
        )
        db.add(existing)
    else:
        existing.score = score
        existing.reasons = reasons
        existing.calculated_at = datetime.now(timezone.utc)
        if existing.status == "stale":
            existing.status = "new"
    return existing


def refresh_broker_posts_for_requirement(db: Session, req: Requirement) -> int:
    """Reverse-match a newly created/updated lead against previously captured broker posts."""
    lead = db.query(Lead).filter(Lead.id == req.lead_id).first()
    if not lead or lead.status not in {"new", "qualifying", "active"}:
        return 0
    posts = db.query(BrokerPost).filter(BrokerPost.status != "ignored").all()
    created_or_updated = 0
    for post in posts:
        match = upsert_broker_feed_match(db, post, req)
        if match:
            created_or_updated += 1
            if post.status not in {"reviewed", "ignored"}:
                post.status = "matched"
    db.flush()
    return created_or_updated


def refresh_broker_post_matches(db: Session, post: BrokerPost) -> list[BrokerFeedMatch]:
    parsed = post.parsed_data or {}
    transaction_type = parsed.get("transaction_type")
    if post.status == "ignored":
        return []
    evidence_keys = ("category", "property_type", "locality", "price", "configuration", "area_sqft")
    has_evidence = any(parsed.get(key) not in (None, "", []) for key in evidence_keys)
    if transaction_type not in {"sale", "rent"} or not has_evidence:
        for old in db.query(BrokerFeedMatch).filter_by(broker_post_id=post.id).all():
            if old.status in {"new", "shortlisted"}:
                old.status = "stale"
        post.status = "needs_review"
        return []

    requirements = db.query(Requirement).join(Lead).options(
        joinedload(Requirement.lead).joinedload(Lead.contact)
    ).filter(Lead.status.in_(["new", "qualifying", "active"])).all()
    for req in requirements:
        upsert_broker_feed_match(db, post, req)

    db.flush()
    count = db.query(BrokerFeedMatch).filter(
        BrokerFeedMatch.broker_post_id == post.id,
        BrokerFeedMatch.status.notin_(["stale", "rejected"])
    ).count()
    if post.status != "reviewed":
        if count:
            post.status = "matched"
        elif parsed.get("confidence", 0) < 35:
            post.status = "needs_review"
        else:
            post.status = "parsed"
    return db.query(BrokerFeedMatch).filter(
        BrokerFeedMatch.broker_post_id == post.id,
        BrokerFeedMatch.status != "stale"
    ).order_by(BrokerFeedMatch.score.desc()).all()


def create_broker_post(db: Session, *, group_id: int, raw_text: str,
                       sender_name: str | None = None, sender_phone: str | None = None,
                       source_type: str = "manual", external_message_id: str | None = None,
                       received_at: datetime | None = None, user_id: int | None = None):
    clean_text = raw_text.strip()
    normalised = re.sub(r"\s+", " ", clean_text.casefold()).strip()
    digest = hashlib.sha256(normalised.encode("utf-8")).hexdigest()
    if external_message_id:
        prior = db.query(BrokerPost).filter(BrokerPost.external_message_id == external_message_id).first()
        if prior:
            return prior, True
    # Avoid repeated imports of the same long listing from one group. Short generic
    # messages are not deduplicated because many unrelated posts share their wording.
    if len(normalised) >= 35:
        prior = db.query(BrokerPost).filter(
            BrokerPost.group_id == group_id,
            BrokerPost.content_hash == digest,
        ).order_by(BrokerPost.created_at.desc()).first()
        if prior:
            return prior, True
    parsed = parse_broker_post(clean_text)
    extracted_phones = parsed.get("phone_numbers") or []
    source_phone = sender_phone or (extracted_phones[0] if extracted_phones else None)
    post = BrokerPost(
        group_id=group_id, source_type=source_type,
        external_message_id=external_message_id, sender_name=(sender_name or "").strip() or None,
        sender_phone=clean_phone(source_phone), raw_text=clean_text,
        content_hash=digest, received_at=received_at,
        parsed_data=parsed, parse_confidence=int(parsed.get("confidence", 0)),
        parse_notes=" ".join(parsed.get("extraction_notes") or []) or None,
        status="new", created_by=user_id,
    )
    db.add(post)
    db.flush()
    refresh_broker_post_matches(db, post)
    log_activity(db, user_id, "broker_post", post.id, "capture",
                 f"Captured broker post from group #{group_id}")
    db.flush()
    return post, False



def run_broker_posts_ocr(db: Session, posts: list[BrokerPost]) -> None:
    """OCR all supplied posts in one local Vision process, then reparse and rematch."""
    media_dir = DATA_DIR / "broker_feed" / "attachments"
    paths_by_post: dict[int, list[Path]] = {}
    all_paths: list[Path] = []
    for post in posts:
        paths = []
        for attachment in (post.attachments or []):
            stored = attachment.get("stored_name", "")
            path = (media_dir / stored).resolve()
            if path.parent == media_dir.resolve() and path.is_file():
                if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".tif", ".tiff", ".pdf"}:
                    paths.append(path)
        paths_by_post[post.id] = paths
        all_paths.extend(paths)

    ocr_result = extract_text_by_media(all_paths)
    texts = ocr_result.get("texts", {})
    for post in posts:
        paths = paths_by_post.get(post.id, [])
        if not paths:
            post.ocr_status = "not_applicable"
            post.ocr_detail = "No image or PDF attachments."
            post.ocr_text = None
        else:
            post.ocr_status = ocr_result["status"]
            post.ocr_detail = ocr_result.get("detail")
            found = [texts.get(str(path), "") for path in paths]
            post.ocr_text = "\n".join(value for value in found if value).strip() or None
        combined = "\n".join(part for part in (post.raw_text, post.ocr_text or "") if part).strip()
        parsed = parse_broker_post(combined)
        post.parsed_data = parsed
        post.parse_confidence = int(parsed.get("confidence", 0))
        post.parse_notes = " ".join(parsed.get("extraction_notes") or []) or None
        if not post.sender_phone and parsed.get("phone_numbers"):
            post.sender_phone = clean_phone(parsed["phone_numbers"][0])
        refresh_broker_post_matches(db, post)


def run_broker_post_ocr(db: Session, post: BrokerPost) -> None:
    """OCR one post locally and refresh its extracted details and lead matches."""
    run_broker_posts_ocr(db, [post])


def broker_post_payload(db: Session, post: BrokerPost):
    matches = db.query(BrokerFeedMatch).filter(
        BrokerFeedMatch.broker_post_id == post.id,
        BrokerFeedMatch.status.notin_(["stale", "rejected"]),
    ).order_by(BrokerFeedMatch.score.desc()).limit(5).all()
    match_rows = []
    for match in matches:
        req = db.query(Requirement).options(
            joinedload(Requirement.lead).joinedload(Lead.contact)
        ).filter(Requirement.id == match.requirement_id).first()
        if not req or not req.lead or req.lead.status in {"converted", "lost"}:
            continue
        match_rows.append({
            "id": match.id, "score": match.score, "status": match.status,
            "reasons": match.reasons or [],
            "lead": {"id": req.lead.id, "lead_code": req.lead.lead_code,
                     "name": req.lead.contact.name, "phone": req.lead.contact.phone,
                     "lead_type": req.lead.lead_type},
        })
    return {
        "id": post.id, "group_id": post.group_id,
        "group_name": post.group.name if post.group else "Unknown group",
        "source_type": post.source_type, "sender_name": post.sender_name,
        "sender_phone": post.sender_phone, "raw_text": post.raw_text,
        "received_at": post.received_at.isoformat() if post.received_at else None,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "parsed_data": post.parsed_data or {}, "parse_confidence": post.parse_confidence,
        "parse_notes": post.parse_notes, "broker_phone_candidates": (post.parsed_data or {}).get("phone_numbers", []),
        "ocr_text": post.ocr_text,
        "ocr_status": post.ocr_status, "ocr_detail": post.ocr_detail,
        "status": post.status, "attachments": post.attachments or [], "match_count": len(match_rows),
        "matches": match_rows,
    }


@app.get("/api/setup/status")
def setup_status(db: Session = Depends(get_db)):
    return {"needs_setup": db.query(User).count() == 0}

@app.post("/api/setup")
def setup_admin(data: SetupIn, response: Response, db: Session = Depends(get_db)):
    if db.query(User).count() > 0:
        raise HTTPException(status_code=409, detail="Initial setup has already been completed")
    username = data.username.strip().lower()
    user = User(username=username, full_name=data.full_name.strip(), password_hash=hash_password(data.password), role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    response.set_cookie(COOKIE_NAME, create_session(user.id), httponly=True, samesite="lax", secure=False, max_age=604800, path="/")
    return {"id": user.id, "username": user.username, "full_name": user.full_name, "role": user.role}

@app.post("/api/login")
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.username) == data.username.strip().lower()).first()
    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    response.set_cookie(COOKIE_NAME, create_session(user.id), httponly=True, samesite="lax", secure=False, max_age=604800, path="/")
    return {"id": user.id, "username": user.username, "full_name": user.full_name, "role": user.role}

@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}

@app.get("/api/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "full_name": user.full_name, "role": user.role}

@app.get("/api/users")
def list_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [{"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role, "is_active": u.is_active}
            for u in db.query(User).order_by(User.full_name).all()]

@app.post("/api/users")
def create_user(data: UserIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    username = data.username.strip().lower()
    if data.role not in {"manager", "agent"}:
        raise HTTPException(status_code=400, detail="New team members must be manager or agent")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    u = User(username=username, full_name=data.full_name.strip(), password_hash=hash_password(data.password), role=data.role)
    db.add(u); db.commit(); db.refresh(u)
    log_activity(db, admin.id, "user", u.id, "create", f"Created team user {u.username}")
    db.commit()
    return {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role}

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    total_leads = db.query(Lead).count()
    active_leads = db.query(Lead).filter(Lead.status.in_(["new", "qualifying", "active"])).count()
    total_properties = db.query(Property).count()
    available_properties = db.query(Property).filter(Property.status == "available").count()
    open_tasks = db.query(Task).filter(Task.status == "open").count()
    overdue_tasks = db.query(Task).filter(Task.status == "open", Task.due_at.is_not(None), Task.due_at < datetime.now(timezone.utc)).count()
    pending_matches = db.query(Match).filter(Match.status == "new").count() + db.query(BrokerFeedMatch).filter(BrokerFeedMatch.status == "new").count()
    broker_feed_posts = db.query(BrokerPost).count()
    broker_feed_matches = db.query(BrokerFeedMatch).filter(BrokerFeedMatch.status.notin_(["stale", "rejected"])).count()
    unreviewed_broker_posts = db.query(BrokerPost).filter(BrokerPost.status.in_(["new", "matched", "needs_review", "parsed"])).count()
    recent_leads = db.query(Lead).options(joinedload(Lead.contact), joinedload(Lead.requirement), joinedload(Lead.assignee)).order_by(Lead.created_at.desc()).limit(6).all()
    upcoming = db.query(Task).filter(Task.status == "open").order_by(Task.due_at.asc().nullslast()).limit(6).all()
    return {
        "stats": {"total_leads": total_leads, "active_leads": active_leads, "total_properties": total_properties,
                  "available_properties": available_properties, "open_tasks": open_tasks, "overdue_tasks": overdue_tasks,
                  "new_matches": pending_matches, "broker_feed_posts": broker_feed_posts,
                  "broker_feed_matches": broker_feed_matches, "unreviewed_broker_posts": unreviewed_broker_posts},
        "recent_leads": [lead_payload(x) for x in recent_leads],
        "tasks": [{"id": t.id, "title": t.title, "due_at": t.due_at.isoformat() if t.due_at else None,
                   "priority": t.priority, "lead_id": t.lead_id} for t in upcoming]
    }

@app.get("/api/leads")
def list_leads(q: str = Query(default=""), status: str = "", lead_type: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Lead).options(joinedload(Lead.contact), joinedload(Lead.requirement), joinedload(Lead.assignee))
    if status: query = query.filter(Lead.status == status)
    if lead_type: query = query.filter(Lead.lead_type == lead_type)
    if q.strip():
        term = f"%{q.strip()}%"
        query = query.join(Contact).filter(or_(Contact.name.ilike(term), Contact.phone.ilike(term), Lead.lead_code.ilike(term), Lead.source.ilike(term)))
    rows = query.order_by(Lead.created_at.desc()).limit(500).all()
    return [lead_payload(x) for x in rows]

@app.post("/api/leads")
def create_lead(data: LeadIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if data.lead_type not in {"buyer", "tenant", "investor", "owner"}:
        raise HTTPException(status_code=400, detail="Invalid lead type")
    if data.status not in {"new", "qualifying", "active", "paused", "converted", "lost"}:
        raise HTTPException(status_code=400, detail="Invalid lead status")
    if data.priority not in {"low", "normal", "high", "urgent"}:
        raise HTTPException(status_code=400, detail="Invalid lead priority")
    if data.transaction_type not in {"sale", "rent"} or data.category not in {"residential", "commercial"}:
        raise HTTPException(status_code=400, detail="Invalid transaction type or property category")
    if data.min_budget is not None and data.min_budget < 0 or data.max_budget is not None and data.max_budget < 0:
        raise HTTPException(status_code=400, detail="Budget values cannot be negative")
    if data.min_budget is not None and data.max_budget is not None and data.min_budget > data.max_budget:
        raise HTTPException(status_code=400, detail="Minimum budget cannot exceed maximum budget")
    if data.stretch_budget is not None and data.max_budget is not None and data.stretch_budget < data.max_budget:
        raise HTTPException(status_code=400, detail="Stretch budget cannot be lower than maximum budget")
    phone = clean_phone(data.phone)
    contact = db.query(Contact).filter(Contact.phone == phone).first() if phone else None
    if not contact:
        contact = Contact(name=data.name.strip(), phone=phone, email=data.email, company=data.company, contact_kind=data.lead_type, notes=data.notes)
        db.add(contact); db.flush()
    else:
        # Keep the canonical contact, but fill gaps rather than overwriting known details.
        contact.name = contact.name or data.name.strip()
        contact.email = contact.email or data.email
        contact.company = contact.company or data.company
    next_id = (db.query(func.max(Lead.id)).scalar() or 0) + 1
    lead = Lead(lead_code=f"LD-{datetime.now().year}-{next_id:05d}", contact_id=contact.id,
                lead_type=data.lead_type, status=data.status, priority=data.priority, source=data.source,
                assigned_to=data.assigned_to or user.id, notes=data.notes, created_by=user.id)
    req = Requirement(
        transaction_type=data.transaction_type, category=data.category, property_type=data.property_type,
        city=data.city, preferred_locations=data.preferred_locations, min_budget=data.min_budget,
        max_budget=data.max_budget, stretch_budget=data.stretch_budget, configuration=data.configuration,
        min_area_sqft=data.min_area_sqft, max_area_sqft=data.max_area_sqft, furnishing=data.furnishing,
        parking_required=data.parking_required, amenities=data.amenities, strict_location=data.strict_location,
        strict_configuration=data.strict_configuration, move_timeline=data.move_timeline, notes=data.requirement_notes)
    lead.requirement = req
    db.add(lead); db.flush()
    log_activity(db, user.id, "lead", lead.id, "create", f"Created {lead.lead_code} for {contact.name}")
    # Create first-pass matches immediately; the user can review them in Matching Centre.
    refresh_matches(db, lead.id)
    refresh_broker_posts_for_requirement(db, req)
    db.commit()
    lead = db.query(Lead).options(joinedload(Lead.contact), joinedload(Lead.requirement), joinedload(Lead.assignee)).get(lead.id)
    return lead_payload(lead)

@app.get("/api/leads/{lead_id}")
def get_lead(lead_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lead = db.query(Lead).options(joinedload(Lead.contact), joinedload(Lead.requirement), joinedload(Lead.assignee)).filter(Lead.id == lead_id).first()
    if not lead: raise HTTPException(status_code=404, detail="Lead not found")
    return lead_payload(lead)

@app.patch("/api/leads/{lead_id}")
def update_lead(lead_id: int, data: LeadUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lead = db.query(Lead).options(joinedload(Lead.contact)).filter(Lead.id == lead_id).first()
    if not lead: raise HTTPException(status_code=404, detail="Lead not found")
    values = data.model_dump(exclude_unset=True)
    if values.get("status") and values["status"] not in {"new", "qualifying", "active", "paused", "converted", "lost"}:
        raise HTTPException(status_code=400, detail="Invalid lead status")
    if values.get("priority") and values["priority"] not in {"low", "normal", "high", "urgent"}:
        raise HTTPException(status_code=400, detail="Invalid lead priority")
    for key in ("status", "priority", "source", "assigned_to", "notes"):
        if key in values: setattr(lead, key, values[key])
    for key in ("name", "email"):
        if key in values: setattr(lead.contact, key, values[key])
    if "phone" in values: lead.contact.phone = clean_phone(values["phone"])
    if lead.requirement:
        if lead.status in {"new", "qualifying", "active"}:
            refresh_broker_posts_for_requirement(db, lead.requirement)
        else:
            for feed_match in db.query(BrokerFeedMatch).filter_by(requirement_id=lead.requirement.id).all():
                if feed_match.status in {"new", "shortlisted"}:
                    feed_match.status = "stale"
    log_activity(db, user.id, "lead", lead.id, "update", f"Updated {lead.lead_code}")
    db.commit()
    lead = db.query(Lead).options(joinedload(Lead.contact), joinedload(Lead.requirement), joinedload(Lead.assignee)).filter(Lead.id == lead_id).first()
    return lead_payload(lead)

@app.get("/api/properties")
def list_properties(q: str = Query(default=""), status: str = "", category: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Property)
    if status: query = query.filter(Property.status == status)
    if category: query = query.filter(Property.category == category)
    if q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(or_(Property.title.ilike(term), Property.property_code.ilike(term), Property.city.ilike(term), Property.locality.ilike(term), Property.property_type.ilike(term)))
    return [property_payload(p) for p in query.order_by(Property.created_at.desc()).limit(500).all()]

@app.post("/api/properties")
def create_property(data: PropertyIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if data.transaction_type not in {"sale", "rent"} or data.category not in {"residential", "commercial"}:
        raise HTTPException(status_code=400, detail="Invalid transaction type or property category")
    if data.status not in {"draft", "available", "on_hold", "under_negotiation", "sold", "rented", "archived"}:
        raise HTTPException(status_code=400, detail="Invalid property status")
    next_id = (db.query(func.max(Property.id)).scalar() or 0) + 1
    owner = None
    if data.owner_name or data.owner_phone:
        phone = clean_phone(data.owner_phone)
        owner = db.query(Contact).filter(Contact.phone == phone).first() if phone else None
        if not owner:
            owner = Contact(name=(data.owner_name or "Property owner"), phone=phone, contact_kind="owner")
            db.add(owner); db.flush()
    source = None
    if data.source_name or data.source_phone:
        phone = clean_phone(data.source_phone)
        source = db.query(Contact).filter(Contact.phone == phone).first() if phone else None
        if not source:
            source = Contact(name=(data.source_name or "Property source"), phone=phone, contact_kind="broker")
            db.add(source); db.flush()
    p = Property(property_code=f"PR-{datetime.now().year}-{next_id:05d}", title=data.title.strip(),
                 transaction_type=data.transaction_type, category=data.category, property_type=data.property_type,
                 city=data.city, locality=data.locality, address=data.address, price=data.price, bhk=data.bhk,
                 area_sqft=data.area_sqft, furnishing=data.furnishing, floor=data.floor, parking=data.parking,
                 amenities=data.amenities, status=data.status, source_type=data.source_type,
                 owner_contact_id=owner.id if owner else None, source_contact_id=source.id if source else None,
                 asking_commission=data.asking_commission, notes=data.notes, assigned_to=data.assigned_to or user.id,
                 created_by=user.id)
    db.add(p); db.flush()
    log_activity(db, user.id, "property", p.id, "create", f"Created {p.property_code}: {p.title}")
    # Reverse matching: discover existing leads that may fit this new listing.
    refresh_matches_for_property(db, p.id)
    db.commit(); db.refresh(p)
    return property_payload(p)

@app.patch("/api/properties/{property_id}")
def update_property(property_id: int, data: PropertyUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.query(Property).filter(Property.id == property_id).first()
    if not p: raise HTTPException(status_code=404, detail="Property not found")
    values = data.model_dump(exclude_unset=True)
    if values.get("status") and values["status"] not in {"draft", "available", "on_hold", "under_negotiation", "sold", "rented", "archived"}:
        raise HTTPException(status_code=400, detail="Invalid property status")
    if values.get("price") is not None and values["price"] <= 0:
        raise HTTPException(status_code=400, detail="Price must be greater than zero")
    for key in ("status", "price", "notes", "locality", "assigned_to"):
        if key in values: setattr(p, key, values[key])
    if values.get("verified") is True: p.verified_at = datetime.now(timezone.utc)
    log_activity(db, user.id, "property", p.id, "update", f"Updated {p.property_code}")
    refresh_matches_for_property(db, p.id)
    db.commit(); db.refresh(p)
    return property_payload(p)

@app.get("/api/matches")
def get_matches(lead_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lead = db.query(Lead).options(joinedload(Lead.requirement)).filter(Lead.id == lead_id).first()
    if not lead: raise HTTPException(status_code=404, detail="Lead not found")
    if not lead.requirement: return []
    matches = refresh_matches(db, lead.id)
    db.commit()
    return [{"id": m.id, "score": m.score, "status": m.status, "reasons": m.reasons,
             "property": property_payload(m.property)} for m in matches]

@app.get("/api/matches/by-property")
def matches_for_property(property_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop: raise HTTPException(status_code=404, detail="Property not found")
    matches = refresh_matches_for_property(db, prop.id)
    db.commit()
    output = []
    for m in matches:
        # Requirement IDs and lead IDs are different; resolve the linked lead safely.
        req = db.query(Requirement).options(joinedload(Requirement.lead).joinedload(Lead.contact)).filter(Requirement.id == m.requirement_id).first()
        if not req or not req.lead or req.lead.status in {"converted", "lost"}: continue
        output.append({"id": m.id, "score": m.score, "status": m.status, "reasons": m.reasons,
                       "lead": {"id": req.lead.id, "lead_code": req.lead.lead_code, "name": req.lead.contact.name,
                                "phone": req.lead.contact.phone, "lead_type": req.lead.lead_type,
                                "status": req.lead.status}})
    return output

@app.patch("/api/matches/{match_id}")
def update_match(match_id: int, payload: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    status = payload.get("status")
    if status not in {"new", "approved", "sent", "rejected", "shortlisted"}:
        raise HTTPException(status_code=400, detail="Invalid match status")
    m = db.query(Match).filter(Match.id == match_id).first()
    if not m: raise HTTPException(status_code=404, detail="Match not found")
    m.status = status
    log_activity(db, user.id, "match", m.id, "status", f"Match marked {status}")
    db.commit()
    return {"ok": True, "status": m.status}



@app.get("/api/broker-feed/groups")
def list_broker_groups(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ensure_broker_groups(db)
    db.commit()
    groups = db.query(BrokerGroup).order_by(BrokerGroup.sort_order, BrokerGroup.id).all()
    output = []
    for group in groups:
        output.append({
            "id": group.id, "name": group.name, "platform": group.platform,
            "is_active": group.is_active, "notes": group.notes,
            "post_count": db.query(BrokerPost).filter(BrokerPost.group_id == group.id).count(),
        })
    return output


@app.patch("/api/broker-feed/groups/{group_id}")
def update_broker_group(group_id: int, data: BrokerGroupUpdate,
                        db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group = db.query(BrokerGroup).filter(BrokerGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Broker group not found")
    values = data.model_dump(exclude_unset=True)
    if "name" in values:
        next_name = values["name"].strip()
        duplicate_name = db.query(BrokerGroup).filter(
            func.lower(BrokerGroup.name) == next_name.lower(), BrokerGroup.id != group.id
        ).first()
        if duplicate_name:
            raise HTTPException(status_code=409, detail="A source group with this name already exists")
        group.name = next_name
    for key in ("is_active", "notes"):
        if key in values:
            setattr(group, key, values[key])
    db.commit()
    return {"id": group.id, "name": group.name, "is_active": group.is_active, "notes": group.notes}


@app.get("/api/broker-feed/posts")
def list_broker_posts(group_id: int | None = None, status: str = "", q: str = "",
                      db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(BrokerPost).options(joinedload(BrokerPost.group))
    if group_id:
        query = query.filter(BrokerPost.group_id == group_id)
    if status:
        query = query.filter(BrokerPost.status == status)
    if q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(or_(BrokerPost.raw_text.ilike(term), BrokerPost.sender_name.ilike(term), BrokerPost.sender_phone.ilike(term)))
    rows = query.order_by(BrokerPost.received_at.desc().nullslast(), BrokerPost.created_at.desc()).limit(300).all()
    return [broker_post_payload(db, post) for post in rows]


@app.post("/api/broker-feed/posts")
def capture_broker_post(data: BrokerPostIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group = db.query(BrokerGroup).filter(BrokerGroup.id == data.group_id, BrokerGroup.is_active.is_(True)).first()
    if not group:
        raise HTTPException(status_code=404, detail="Active broker group not found")
    received_at = None
    if data.received_at:
        try:
            received_at = datetime.fromisoformat(data.received_at.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid received_at timestamp")
    post, duplicate = create_broker_post(
        db, group_id=group.id, raw_text=data.raw_text,
        sender_name=data.sender_name, sender_phone=data.sender_phone,
        source_type="manual", external_message_id=data.source_message_id,
        received_at=received_at, user_id=user.id,
    )
    db.commit()
    db.refresh(post)
    payload = broker_post_payload(db, post)
    payload["duplicate"] = duplicate
    return payload


@app.post("/api/broker-feed/import-export")
async def import_whatsapp_export(group_id: int = Form(...), file: UploadFile = File(...),
                                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group = db.query(BrokerGroup).filter(BrokerGroup.id == group_id, BrokerGroup.is_active.is_(True)).first()
    if not group:
        raise HTTPException(status_code=404, detail="Active broker group not found")
    filename = (file.filename or "").lower()
    if not (filename.endswith(".txt") or filename.endswith(".zip")):
        raise HTTPException(status_code=400, detail="Upload a WhatsApp chat export .txt or .zip file")
    content = await file.read()
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Export file is larger than 100 MB")

    media_archive = None
    if filename.endswith(".zip"):
        try:
            media_archive = zipfile.ZipFile(io.BytesIO(content))
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="The uploaded ZIP file is invalid")
        members = [n for n in media_archive.namelist() if n.lower().endswith(".txt") and not n.endswith("/")]
        if not members:
            raise HTTPException(status_code=400, detail="No WhatsApp .txt chat file was found inside the ZIP")
        txt_member = max(members, key=lambda n: media_archive.getinfo(n).file_size)
        if media_archive.getinfo(txt_member).file_size > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="The chat text file inside the ZIP is larger than 10 MB")
        text = media_archive.read(txt_member).decode("utf-8-sig", errors="replace")
        media_by_name = {}
        total_uncompressed = 0
        for member in media_archive.infolist():
            if member.is_dir():
                continue
            total_uncompressed += member.file_size
            if total_uncompressed > 300 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="ZIP expands beyond the 300 MB safety limit")
            base = Path(member.filename).name
            if base and not base.startswith("."):
                media_by_name[base.casefold()] = member
    else:
        text = content.decode("utf-8-sig", errors="replace")
        media_by_name = {}

    messages = split_whatsapp_export(text)
    imported = duplicates = skipped = media_attached = 0
    skipped_demand = skipped_mixed = split_message_count = entries_detected = 0
    posts_for_ocr: dict[int, BrokerPost] = {}
    media_dir = DATA_DIR / "broker_feed" / "attachments"
    media_dir.mkdir(parents=True, exist_ok=True)
    media_pattern = re.compile(r"([^\s<>:\"']+\.(?:jpe?g|png|webp|gif|heic|tiff?|pdf|mp4|mov))", re.I)
    allowed_media = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/heic", "image/tiff",
                     "application/pdf", "video/mp4", "video/quicktime"}

    for message in messages:
        original_raw = message.get("text", "").strip()
        if len(original_raw) < 3:
            skipped += 1
            continue

        # Segment first, then classify each segment independently. A single broker
        # message may contain several available properties followed by client
        # requirements. Classifying the entire message first would hide all supply
        # entries inside a mixed post. The splitter keeps the requirement section
        # separate and does not inherit an availability heading into that section.
        entries = split_property_entries(original_raw)
        if len(entries) > 1:
            split_message_count += 1
            entries_detected += len(entries)
        parent_digest = hashlib.sha256(
            f"{group.id}|{message.get('date','')}|{message.get('time','')}|{message.get('sender','')}|{original_raw}".encode("utf-8")
        ).hexdigest()
        received_at = parse_export_datetime(message.get("date", ""), message.get("time", ""))

        for entry_index, raw in enumerate(entries, start=1):
            raw = raw.strip()
            if len(raw) < 3:
                skipped += 1
                continue
            intent = classify_broker_message(raw)
            if intent == "demand":
                # Broker requirements are demand-side information, not available
                # supply. They must never be compared as property candidates.
                skipped_demand += 1
                continue

            parsed = parse_broker_post(raw)
            intent = parsed.get("message_intent") or intent
            if intent == "demand":
                skipped_demand += 1
                continue
            if intent == "mixed":
                skipped_mixed += 1
            referenced_media = []
            if media_archive:
                for media_match in media_pattern.finditer(raw):
                    media_name = Path(media_match.group(1).strip()).name
                    member = media_by_name.get(media_name.casefold())
                    if member and member.file_size <= 15 * 1024 * 1024:
                        referenced_media.append((media_name, member))

            has_supply_evidence = bool(
                parsed.get("transaction_type") or parsed.get("property_type") or
                parsed.get("configuration") or parsed.get("locality") or parsed.get("price")
            )
            if intent == "unknown" and not referenced_media:
                skipped += 1
                continue
            if intent == "supply" and not has_supply_evidence and not referenced_media:
                skipped += 1
                continue
            if intent == "mixed":
                # Preserve the original for review, but parse_broker_post leaves
                # matchable property fields blank so no automatic lead match occurs.
                pass

            external_id = f"wa:{parent_digest}:{entry_index}"
            post, is_duplicate = create_broker_post(
                db, group_id=group.id, raw_text=raw,
                sender_name=message.get("sender") or None,
                source_type="whatsapp_export", external_message_id=external_id,
                received_at=received_at, user_id=user.id,
            )
            if len(entries) > 1:
                details = dict(post.parsed_data or {})
                details.update({
                    "source_message_hash": parent_digest,
                    "source_entry_index": entry_index,
                    "source_entry_count": len(entries),
                    "source_message_text": original_raw,
                })
                post.parsed_data = details
            if is_duplicate:
                duplicates += 1
            else:
                imported += 1

            if media_archive:
                saved = list(post.attachments or [])
                existing_names = {a.get("filename") for a in saved}
                for media_name, member in referenced_media:
                    if media_name in existing_names:
                        continue
                    media_bytes = media_archive.read(member)
                    content_type = mimetypes.guess_type(media_name)[0] or "application/octet-stream"
                    if content_type not in allowed_media:
                        continue
                    suffix = Path(media_name).suffix.lower()
                    stored_name = f"{uuid.uuid4().hex}{suffix}"
                    (media_dir / stored_name).write_bytes(media_bytes)
                    saved.append({"filename": media_name, "stored_name": stored_name,
                                  "content_type": content_type, "size": len(media_bytes)})
                    existing_names.add(media_name)
                    media_attached += 1
                if saved != (post.attachments or []):
                    post.attachments = saved
                if any(Path(a.get("filename", "")).suffix.lower() in {
                    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".tif", ".tiff", ".pdf"
                } for a in saved):
                    posts_for_ocr[post.id] = post

    if media_archive:
        media_archive.close()
    if posts_for_ocr:
        run_broker_posts_ocr(db, list(posts_for_ocr.values()))
    db.commit()
    return {
        "ok": True, "group": group.name, "messages_seen": len(messages),
        "imported": imported, "duplicates": duplicates,
        "skipped_non_property": skipped, "skipped_demand": skipped_demand,
        "mixed_messages_for_review": skipped_mixed,
        "multi_listing_messages_split": split_message_count,
        "listing_entries_from_splits": entries_detected,
        "media_attached": media_attached, "posts_ocr_processed": len(posts_for_ocr),
    }


@app.post("/api/broker-feed/posts/{post_id}/attachments")
async def upload_broker_post_attachments(post_id: int, files: list[UploadFile] = File(...),
                                         db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    post = db.query(BrokerPost).filter(BrokerPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Broker post not found")
    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/heic", "image/tiff", "application/pdf"}
    target_dir = DATA_DIR / "broker_feed" / "attachments"
    target_dir.mkdir(parents=True, exist_ok=True)
    saved = list(post.attachments or [])
    for upload in files:
        allowed = allowed | {"video/mp4", "video/quicktime"}
        if upload.content_type not in allowed:
            raise HTTPException(status_code=400, detail=f"Unsupported attachment type: {upload.content_type}")
        data = await upload.read()
        if len(data) > 15 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Each attachment must be 15 MB or smaller")
        suffix = Path(upload.filename or "attachment").suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".tif", ".tiff", ".pdf", ".mp4", ".mov"}:
            suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
                      "image/gif": ".gif", "image/heic": ".heic", "image/tiff": ".tiff",
                      "application/pdf": ".pdf", "video/mp4": ".mp4",
                      "video/quicktime": ".mov"}[upload.content_type]
        stored_name = f"{uuid.uuid4().hex}{suffix}"
        (target_dir / stored_name).write_bytes(data)
        saved.append({"filename": Path(upload.filename or stored_name).name,
                      "stored_name": stored_name, "content_type": upload.content_type,
                      "size": len(data)})
    post.attachments = saved
    run_broker_post_ocr(db, post)
    db.commit()
    return {"ok": True, "attachments": saved, "ocr_status": post.ocr_status,
            "ocr_detail": post.ocr_detail, "match_count": db.query(BrokerFeedMatch).filter(
                BrokerFeedMatch.broker_post_id == post.id,
                BrokerFeedMatch.status.notin_(["stale", "rejected"])).count()}


@app.get("/api/broker-feed/posts/{post_id}/attachments/{attachment_index}")
def get_broker_post_attachment(post_id: int, attachment_index: int,
                              db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    post = db.query(BrokerPost).filter(BrokerPost.id == post_id).first()
    if not post or attachment_index < 0 or attachment_index >= len(post.attachments or []):
        raise HTTPException(status_code=404, detail="Attachment not found")
    attachment = post.attachments[attachment_index]
    file_path = DATA_DIR / "broker_feed" / "attachments" / attachment.get("stored_name", "")
    if not file_path.is_file() or file_path.parent != (DATA_DIR / "broker_feed" / "attachments"):
        raise HTTPException(status_code=404, detail="Attachment file not found")
    return FileResponse(file_path, media_type=attachment.get("content_type", "application/octet-stream"),
                        filename=attachment.get("filename", file_path.name))


@app.post("/api/broker-feed/posts/{post_id}/reprocess")
def reprocess_broker_post(post_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    post = db.query(BrokerPost).options(joinedload(BrokerPost.group)).filter(BrokerPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Broker post not found")
    run_broker_post_ocr(db, post)
    db.commit()
    return broker_post_payload(db, post)


@app.patch("/api/broker-feed/posts/{post_id}")
def update_broker_post(post_id: int, payload: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    post = db.query(BrokerPost).filter(BrokerPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Broker post not found")
    status = payload.get("status")
    if status not in {"reviewed", "ignored"}:
        raise HTTPException(status_code=400, detail="Allowed post actions: reviewed or ignored")
    post.status = status
    db.commit()
    return {"ok": True, "status": post.status}


@app.patch("/api/broker-feed/matches/{match_id}")
def update_broker_feed_match(match_id: int, data: BrokerFeedMatchUpdate,
                             db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if data.status not in {"new", "shortlisted", "contacted", "rejected"}:
        raise HTTPException(status_code=400, detail="Invalid broker-feed match status")
    match = db.query(BrokerFeedMatch).filter(BrokerFeedMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Broker-feed match not found")
    match.status = data.status
    db.commit()
    return {"ok": True, "status": match.status}


@app.get("/api/tasks")
def list_tasks(status: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Task)
    if status: query = query.filter(Task.status == status)
    rows = query.order_by(Task.due_at.asc().nullslast(), Task.created_at.desc()).limit(500).all()
    return [{"id": t.id, "title": t.title, "description": t.description, "due_at": t.due_at.isoformat() if t.due_at else None,
             "priority": t.priority, "status": t.status, "lead_id": t.lead_id, "property_id": t.property_id,
             "assigned_to": t.assigned_to} for t in rows]

@app.post("/api/tasks")
def create_task(data: TaskIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    due = None
    if data.due_at:
        try:
            due = datetime.fromisoformat(data.due_at.replace("Z", "+00:00"))
            if due.tzinfo is None: due = due.replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid due date/time")
    if data.priority not in {"low", "normal", "high", "urgent"}:
        raise HTTPException(status_code=400, detail="Invalid task priority")
    t = Task(title=data.title, description=data.description, due_at=due, priority=data.priority,
             lead_id=data.lead_id, property_id=data.property_id, assigned_to=data.assigned_to or user.id, created_by=user.id)
    db.add(t); db.flush()
    log_activity(db, user.id, "task", t.id, "create", f"Created task: {t.title}")
    db.commit()
    return {"id": t.id, "title": t.title, "status": t.status}

@app.patch("/api/tasks/{task_id}")
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t: raise HTTPException(status_code=404, detail="Task not found")
    values = data.model_dump(exclude_unset=True)
    if values.get("status") and values["status"] not in {"open", "completed", "cancelled"}:
        raise HTTPException(status_code=400, detail="Invalid task status")
    if values.get("priority") and values["priority"] not in {"low", "normal", "high", "urgent"}:
        raise HTTPException(status_code=400, detail="Invalid task priority")
    for k, v in values.items(): setattr(t, k, v)
    db.commit()
    return {"id": t.id, "status": t.status}

@app.get("/api/export/leads.csv")
def export_leads(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Lead).options(joinedload(Lead.contact), joinedload(Lead.requirement)).all()
    buf = io.StringIO(); writer = csv.writer(buf)
    writer.writerow(["Lead ID", "Name", "Phone", "Type", "Status", "Priority", "Source", "Transaction", "Category", "City", "Locations", "Min Budget INR", "Max Budget INR", "Configuration", "Notes"])
    for l in rows:
        r = l.requirement
        writer.writerow([l.lead_code, l.contact.name, l.contact.phone, l.lead_type, l.status, l.priority, l.source,
                         r.transaction_type if r else "", r.category if r else "", r.city if r else "",
                         ", ".join(r.preferred_locations or []) if r else "", r.min_budget if r else "", r.max_budget if r else "",
                         r.configuration if r else "", l.notes or ""])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=property_os_leads.csv"})

@app.get("/api/export/properties.csv")
def export_properties(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Property).all()
    buf = io.StringIO(); writer = csv.writer(buf)
    writer.writerow(["Property ID", "Title", "Transaction", "Category", "Type", "City", "Locality", "Price INR", "Configuration", "Area Sq Ft", "Status", "Notes"])
    for p in rows:
        writer.writerow([p.property_code, p.title, p.transaction_type, p.category, p.property_type, p.city, p.locality or "", p.price, p.bhk or "", p.area_sqft or "", p.status, p.notes or ""])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=property_os_properties.csv"})

@app.get("/api/health")
def health():
    return {"ok": True, "app": "Property OS V2", "version": "2.1.3-mixed-entry-split", "mode": "local-first"}
