from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    """Naive UTC timestamp, so SQLite and Postgres store and return the same thing."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    flat_no: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="resident")  # resident | committee
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    complaints: Mapped[list["Complaint"]] = relationship(back_populates="author")


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30), default="other", index=True)
    urgency: Mapped[str] = mapped_column(String(10), default="medium")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    author: Mapped["User"] = relationship(back_populates="complaints")
    updates: Mapped[list["StatusUpdate"]] = relationship(
        back_populates="complaint",
        order_by="StatusUpdate.id",
        cascade="all, delete-orphan",
    )

    @property
    def author_name(self) -> str:
        return self.author.name

    @property
    def flat_no(self) -> str:
        return self.author.flat_no


class StatusUpdate(Base):
    """Append-only history: one row per status change or note."""

    __tablename__ = "status_updates"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(Text, default="")
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    complaint: Mapped["Complaint"] = relationship(back_populates="updates")
    editor: Mapped["User"] = relationship()

    @property
    def editor_name(self) -> str:
        return self.editor.name
