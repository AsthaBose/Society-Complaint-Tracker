"""Fill the database with demo data so screenshots and demos look real.

Run from the project root:  python -m scripts.seed
Creates: committee@demo.com and resident@demo.com / meera@demo.com (password: password123).
"""
from datetime import timedelta

from app import models
from app.database import Base, SessionLocal, engine
from app.models import Complaint, StatusUpdate, User, utcnow
from app.security import hash_password
from app.triage import keyword_triage

SAMPLES = [
    ("Water leaking from ceiling", "Water is dripping from the bathroom ceiling since last night, wall is damp.", "resident", "resolved", 30),
    ("Lift stuck at 3rd floor", "Lift B stops between floors and the door will not open properly.", "meera", "in_progress", None),
    ("Street light not working", "The light near gate 2 has been off for a week, the area is very dark at night.", "resident", "open", None),
    ("Garbage not collected", "Garbage has not been collected from block C for three days, bad smell.", "meera", "resolved", 52),
    ("Loud music after midnight", "Flat 405 plays loud music on weekends till 2 AM.", "resident", "open", None),
    ("Stranger near parking area", "An unknown person was seen checking car doors in the basement parking.", "meera", "open", None),
]


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).first():
            print("Database already has users; refusing to seed on top of real data.")
            return

        users = {
            "committee": User(name="Ravi Sharma", email="committee@demo.com", flat_no="Office", role="committee",
                              password_hash=hash_password("password123")),
            "resident": User(name="Anita Rao", email="resident@demo.com", flat_no="A-101", role="resident",
                             password_hash=hash_password("password123")),
            "meera": User(name="Meera Iyer", email="meera@demo.com", flat_no="C-305", role="resident",
                          password_hash=hash_password("password123")),
        }
        db.add_all(users.values())
        db.flush()

        now = utcnow()
        for i, (title, desc, who, status, hours) in enumerate(SAMPLES):
            created = now - timedelta(days=len(SAMPLES) - i, hours=3)
            category, urgency = keyword_triage(title, desc)
            c = Complaint(user_id=users[who].id, title=title, description=desc, category=category,
                          urgency=urgency, status=status, created_at=created)
            if status == "resolved":
                c.resolved_at = created + timedelta(hours=hours)
            db.add(c)
            db.flush()
            db.add(StatusUpdate(complaint_id=c.id, status="open", note="Complaint submitted",
                                updated_by=users[who].id, created_at=created))
            if status != "open":
                db.add(StatusUpdate(complaint_id=c.id, status="in_progress", note="Looking into it",
                                    updated_by=users["committee"].id, created_at=created + timedelta(hours=2)))
            if status == "resolved":
                db.add(StatusUpdate(complaint_id=c.id, status="resolved", note="Fixed and verified",
                                    updated_by=users["committee"].id, created_at=c.resolved_at))
        db.commit()
        print("Seeded 3 users and", len(SAMPLES), "complaints.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
