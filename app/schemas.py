from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Category = Literal[
    "plumbing", "electrical", "lift", "security", "cleaning", "parking", "noise", "other"
]
Urgency = Literal["low", "medium", "high"]
Status = Literal["open", "in_progress", "resolved"]

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


# ---------- auth ----------
class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    flat_no: str = Field(min_length=1, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    committee_code: Optional[str] = None


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    flat_no: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- complaints ----------
class ComplaintCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=4000)
    # Optional: when left out, the server fills them in (see triage.py).
    category: Optional[Category] = None
    urgency: Optional[Urgency] = None


class StatusUpdateIn(BaseModel):
    status: Status
    note: str = Field(default="", max_length=1000)


class StatusUpdateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: Status
    note: str
    editor_name: str
    created_at: datetime


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    category: str
    urgency: str
    status: Status
    author_name: str
    flat_no: str
    created_at: datetime
    resolved_at: Optional[datetime] = None


class ComplaintDetail(ComplaintOut):
    updates: list[StatusUpdateOut]


class StatsOut(BaseModel):
    total: int
    open: int
    in_progress: int
    resolved: int
    high_urgency_open: int
    avg_resolution_hours: Optional[float]
    by_category: dict[str, int]
