from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from .database import Base


def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(30), default="agent")  # admin, manager, agent
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Contact(Base):
    __tablename__ = "contacts"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    phone: Mapped[str | None] = mapped_column(String(40), index=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    company: Mapped[str | None] = mapped_column(String(160), nullable=True)
    contact_kind: Mapped[str] = mapped_column(String(40), default="client")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id", ondelete="RESTRICT"), index=True)
    lead_type: Mapped[str] = mapped_column(String(30), default="buyer")
    status: Mapped[str] = mapped_column(String(30), default="new", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal", index=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    contact: Mapped[Contact] = relationship()
    requirement: Mapped["Requirement | None"] = relationship(back_populates="lead", uselist=False, cascade="all, delete-orphan")
    assignee: Mapped[User | None] = relationship(foreign_keys=[assigned_to])

class Requirement(Base):
    __tablename__ = "requirements"
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), unique=True, index=True)
    transaction_type: Mapped[str] = mapped_column(String(20), default="sale")
    category: Mapped[str] = mapped_column(String(30), default="residential")
    property_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    preferred_locations: Mapped[list] = mapped_column(JSON, default=list)
    min_budget: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    max_budget: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    stretch_budget: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    configuration: Mapped[str | None] = mapped_column(String(30), nullable=True)
    min_area_sqft: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_area_sqft: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    furnishing: Mapped[str | None] = mapped_column(String(40), nullable=True)
    parking_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    amenities: Mapped[list] = mapped_column(JSON, default=list)
    strict_location: Mapped[bool] = mapped_column(Boolean, default=False)
    strict_configuration: Mapped[bool] = mapped_column(Boolean, default=False)
    move_timeline: Mapped[str | None] = mapped_column(String(60), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead: Mapped[Lead] = relationship(back_populates="requirement")

class Property(Base):
    __tablename__ = "properties"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(180), index=True)
    transaction_type: Mapped[str] = mapped_column(String(20), default="sale", index=True)
    category: Mapped[str] = mapped_column(String(30), default="residential", index=True)
    property_type: Mapped[str] = mapped_column(String(60), default="apartment")
    city: Mapped[str] = mapped_column(String(100), default="Ahmedabad", index=True)
    locality: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(14, 2))  # INR; rent means monthly rent
    bhk: Mapped[str | None] = mapped_column(String(30), nullable=True)
    area_sqft: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    furnishing: Mapped[str | None] = mapped_column(String(40), nullable=True)
    floor: Mapped[str | None] = mapped_column(String(30), nullable=True)
    parking: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    amenities: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="available", index=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner_contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id"), nullable=True)
    source_contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id"), nullable=True)
    asking_commission: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("requirement_id", "property_id", name="uq_requirement_property"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id", ondelete="CASCADE"), index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    score: Mapped[int] = mapped_column(Integer)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="new")  # new, approved, sent, rejected, shortlisted
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    property: Mapped[Property] = relationship()

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id", ondelete="SET NULL"), nullable=True)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Activity(Base):
    __tablename__ = "activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    activity_type: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class SiteVisit(Base):
    __tablename__ = "site_visits"
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="RESTRICT"), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), default="scheduled")
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

class Deal(Base):
    __tablename__ = "deals"
    id: Mapped[int] = mapped_column(primary_key=True)
    deal_code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="RESTRICT"), index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="RESTRICT"), index=True)
    stage: Mapped[str] = mapped_column(String(30), default="negotiation")
    agreed_value: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    expected_close_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

class Commission(Base):
    __tablename__ = "commissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id", ondelete="CASCADE"), index=True)
    expected_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    agreed_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    received_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    status: Mapped[str] = mapped_column(String(24), default="expected")
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    developer: Mapped[str | None] = mapped_column(String(180), nullable=True)
    city: Mapped[str] = mapped_column(String(100), default="Ahmedabad")
    locality: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category: Mapped[str] = mapped_column(String(30), default="residential")
    rera_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    possession_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

class ProjectUnit(Base):
    __tablename__ = "project_units"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    unit_type: Mapped[str] = mapped_column(String(60))
    price_from: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    price_to: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    availability_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    area_sqft: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="available")

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(30), default="manual")
    direction: Mapped[str] = mapped_column(String(20), default="outbound")
    body: Mapped[str] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    delivery_status: Mapped[str] = mapped_column(String(30), default="not_sent")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(40))
    summary: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

Index("ix_property_match", Property.transaction_type, Property.category, Property.status, Property.city)

class BrokerGroup(Base):
    """A configured source group/feed. Default records represent the five user groups."""
    __tablename__ = "broker_groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    platform: Mapped[str] = mapped_column(String(30), default="whatsapp")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class BrokerPost(Base):
    """A raw post captured from a broker group before it becomes verified inventory."""
    __tablename__ = "broker_posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("broker_groups.id", ondelete="RESTRICT"), index=True)
    source_type: Mapped[str] = mapped_column(String(40), default="manual")
    external_message_id: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    sender_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    sender_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    parsed_data: Mapped[dict] = mapped_column(JSON, default=dict)
    attachments: Mapped[list] = mapped_column(JSON, default=list)
    parse_confidence: Mapped[int] = mapped_column(Integer, default=0)
    parse_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_status: Mapped[str] = mapped_column(String(30), default="pending")
    ocr_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="new", index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    group: Mapped[BrokerGroup] = relationship()


class BrokerFeedMatch(Base):
    """A ranked link between a raw broker post and a saved client requirement."""
    __tablename__ = "broker_feed_matches"
    __table_args__ = (UniqueConstraint("broker_post_id", "requirement_id", name="uq_feed_post_requirement"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    broker_post_id: Mapped[int] = mapped_column(ForeignKey("broker_posts.id", ondelete="CASCADE"), index=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id", ondelete="CASCADE"), index=True)
    score: Mapped[int] = mapped_column(Integer)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="new", index=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    post: Mapped[BrokerPost] = relationship()
    requirement: Mapped[Requirement] = relationship()


class RawMessage(Base):
    """Every inbound provider message, stored untouched before any processing."""
    __tablename__ = "raw_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), default="whatsapp_cloud")
    provider_message_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    from_phone: Mapped[str | None] = mapped_column(String(40), index=True, nullable=True)
    sender_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    msg_type: Mapped[str] = mapped_column(String(30), default="text")
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="received", index=True)
    broker_post_id: Mapped[int | None] = mapped_column(ForeignKey("broker_posts.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
