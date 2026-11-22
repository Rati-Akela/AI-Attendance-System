"""Seed realistic demo data so a fresh deployment has something to explore.

Demo students have no face photos (so face matching can't be demoed without
enrolling someone), but the dashboard, reports and student portal are fully
populated.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from . import db

DEMO_EMAIL = "demo@snapclass.app"
DEMO_PASSWORD = "demo-pass-123"
DEMO_STUDENT_LOGIN = "SC-DEMO01"
DEMO_STUDENT_CODE = "DEMO1234"

_NAMES = [
    "Aarav Sharma",
    "Diya Patel",
    "Vihaan Reddy",
    "Ananya Iyer",
    "Arjun Nair",
    "Ishita Gupta",
    "Kabir Singh",
    "Meera Joshi",
    "Rohan Mehta",
    "Saanvi Rao",
    "Aditya Verma",
    "Navya Menon",
    "Krish Kapoor",
    "Tara Bose",
    "Yash Agarwal",
    "Riya Das",
    "Dev Malhotra",
    "Pooja Hegde",
    "Nikhil Kumar",
    "Sneha Pillai",
]
_SUBJECTS = [
    ("CS301", "Machine Learning"),
    ("CS302", "Database Systems"),
    ("CS303", "Computer Networks"),
]


def seed_demo(conn, classes_per_subject: int = 14) -> int:
    """Create (or return) the demo teacher. Safe to call repeatedly."""
    existing = db.get_teacher_by_email(conn, DEMO_EMAIL)
    if existing:
        return existing["id"]

    rng = random.Random(42)
    tid = db.create_teacher(conn, "Demo Teacher", DEMO_EMAIL, DEMO_PASSWORD)
    sids = []
    for i, name in enumerate(_NAMES, start=1):
        kwargs = {"login_id": DEMO_STUDENT_LOGIN, "access_code": DEMO_STUDENT_CODE} if i == 1 else {}
        sids.append(db.create_student(conn, tid, f"23CS{i:03d}", name, **kwargs)["id"])
    # Each student has a habitual attendance level so the "at risk" list is meaningful.
    habit = {sid: rng.choice([0.97, 0.92, 0.88, 0.82, 0.7, 0.6]) for sid in sids}
    habit[sids[0]] = 0.93

    now = datetime.now(UTC).replace(hour=4, minute=30, second=0, microsecond=0)
    for code, title in _SUBJECTS:
        subject_id = db.create_subject(conn, tid, code, title)
        db.set_enrollment(conn, subject_id, sids)
        for k in range(classes_per_subject):
            when = now - timedelta(days=(classes_per_subject - k) * 2 + rng.randint(0, 1))
            session_id = db.create_session(
                conn, subject_id, faces_detected=0, taken_at=when.isoformat(timespec="seconds")
            )
            records = []
            for sid in sids:
                present = rng.random() < habit[sid]
                records.append((sid, "present" if present else "absent", "manual", None))
            db.save_attendance(conn, session_id, records)
    return tid
