from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any

class SetupIn(BaseModel):
    username: str = Field(min_length=3, max_length=60)
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=10, max_length=128)

class LoginIn(BaseModel):
    username: str
    password: str

class LeadIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    lead_type: str = "buyer"
    status: str = "new"
    priority: str = "normal"
    source: Optional[str] = None
    assigned_to: Optional[int] = None
    notes: Optional[str] = None
    transaction_type: str = "sale"
    category: str = "residential"
    property_type: Optional[str] = None
    city: Optional[str] = "Ahmedabad"
    preferred_locations: list[str] = Field(default_factory=list)
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    stretch_budget: Optional[float] = None
    configuration: Optional[str] = None
    min_area_sqft: Optional[float] = None
    max_area_sqft: Optional[float] = None
    furnishing: Optional[str] = None
    parking_required: Optional[bool] = None
    amenities: list[str] = Field(default_factory=list)
    strict_location: bool = False
    strict_configuration: bool = False
    move_timeline: Optional[str] = None
    requirement_notes: Optional[str] = None

class LeadUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    source: Optional[str] = None
    assigned_to: Optional[int] = None
    notes: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    model_config = ConfigDict(extra="forbid")

class PropertyIn(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    transaction_type: str = "sale"
    category: str = "residential"
    property_type: str = "apartment"
    city: str = "Ahmedabad"
    locality: Optional[str] = None
    address: Optional[str] = None
    price: float = Field(gt=0)
    bhk: Optional[str] = None
    area_sqft: Optional[float] = None
    furnishing: Optional[str] = None
    floor: Optional[str] = None
    parking: Optional[bool] = None
    amenities: list[str] = Field(default_factory=list)
    status: str = "available"
    source_type: Optional[str] = None
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    source_name: Optional[str] = None
    source_phone: Optional[str] = None
    asking_commission: Optional[float] = None
    notes: Optional[str] = None
    assigned_to: Optional[int] = None

class PropertyUpdate(BaseModel):
    status: Optional[str] = None
    price: Optional[float] = None
    notes: Optional[str] = None
    locality: Optional[str] = None
    verified: Optional[bool] = None
    assigned_to: Optional[int] = None
    model_config = ConfigDict(extra="forbid")

class TaskIn(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    description: Optional[str] = None
    due_at: Optional[str] = None
    priority: str = "normal"
    lead_id: Optional[int] = None
    property_id: Optional[int] = None
    assigned_to: Optional[int] = None

class TaskUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    model_config = ConfigDict(extra="forbid")

class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=60)
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=10, max_length=128)
    role: str = "agent"

class BrokerPostIn(BaseModel):
    group_id: int
    raw_text: str = Field(min_length=3, max_length=20000)
    sender_name: Optional[str] = None
    sender_phone: Optional[str] = None
    source_message_id: Optional[str] = None
    received_at: Optional[str] = None

class BrokerGroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=140)
    is_active: Optional[bool] = None
    notes: Optional[str] = None

class BrokerFeedMatchUpdate(BaseModel):
    status: str
