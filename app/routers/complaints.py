from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..deps import get_current_user, get_db, require_committee
from ..models import Complaint, StatusUpdate, User, utcnow
from ..schemas import (
    Category,
    ComplaintCreate,
    ComplaintDetail,
    ComplaintOut,
    StatsOut,
    Status,
    StatusUpdateIn,
)
from ..stats import compute_stats
from ..triage import keyword_triage

router = APIRouter(prefix="/api", tags=["complaints"])


def _visible_complaint(db: Session, complaint_id: int, user: User) -> Complaint:
    """Residents only see their own complaints. Someone else's complaint returns 404, not 403,
    so the API does not even confirm that the id exists."""
    complaint = db.get(Complaint, complaint_id)
    if complaint is None or (user.role != "committee" and complaint.user_id != user.id):
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


@router.post("/complaints", response_model=ComplaintOut, status_code=201)
def create_complaint(
    data: ComplaintCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    guessed_category, guessed_urgency = keyword_triage(data.title, data.description)
    complaint = Complaint(
        user_id=user.id,
        title=data.title.strip(),
        description=data.description.strip(),
        category=data.category or guessed_category,
        urgency=data.urgency or guessed_urgency,
    )
    db.add(complaint)
    db.flush()  # assigns complaint.id
    db.add(
        StatusUpdate(
            complaint_id=complaint.id, status="open", note="Complaint submitted", updated_by=user.id
        )
    )
    db.commit()
    db.refresh(complaint)
    return complaint


@router.get("/complaints", response_model=list[ComplaintOut])
def list_complaints(
    status_filter: Optional[Status] = Query(None, alias="status"),
    category: Optional[Category] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Complaint)
        .options(joinedload(Complaint.author))
        .order_by(Complaint.created_at.desc(), Complaint.id.desc())
    )
    if user.role != "committee":
        stmt = stmt.where(Complaint.user_id == user.id)
    if status_filter:
        stmt = stmt.where(Complaint.status == status_filter)
    if category:
        stmt = stmt.where(Complaint.category == category)
    return db.scalars(stmt).all()


@router.get("/complaints/{complaint_id}", response_model=ComplaintDetail)
def get_complaint(
    complaint_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _visible_complaint(db, complaint_id, user)


@router.patch("/complaints/{complaint_id}/status", response_model=ComplaintDetail)
def update_status(
    complaint_id: int,
    data: StatusUpdateIn,
    user: User = Depends(require_committee),
    db: Session = Depends(get_db),
):
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")

    note = data.note.strip()
    if data.status == complaint.status and not note:
        raise HTTPException(status_code=400, detail="Nothing to update: same status and no note")

    complaint.status = data.status
    if data.status == "resolved":
        if complaint.resolved_at is None:
            complaint.resolved_at = utcnow()
    else:
        complaint.resolved_at = None  # reopened

    db.add(StatusUpdate(complaint_id=complaint.id, status=data.status, note=note, updated_by=user.id))
    db.commit()
    db.refresh(complaint)
    return complaint


@router.get("/stats", response_model=StatsOut)
def stats(user: User = Depends(require_committee), db: Session = Depends(get_db)):
    return compute_stats(db.scalars(select(Complaint)).all())
