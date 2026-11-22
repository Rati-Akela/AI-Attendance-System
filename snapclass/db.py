"""SQLite persistence layer.

Only face *embeddings* (128 numbers per photo) are stored - never the photos
themselves - which keeps the database small and limits privacy exposure.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from . import auth
from .config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS teachers (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS subjects (
    id         INTEGER PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    code       TEXT NOT NULL,
    name       TEXT NOT NULL,
    UNIQUE (teacher_id, code)
);
CREATE TABLE IF NOT EXISTS students (
    id          INTEGER PRIMARY KEY,
    teacher_id  INTEGER NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    roll_no     TEXT NOT NULL,
    name        TEXT NOT NULL,
    email       TEXT,
    login_id    TEXT NOT NULL UNIQUE,
    access_hash TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    UNIQUE (teacher_id, roll_no)
);
CREATE TABLE IF NOT EXISTS face_encodings (
    id         INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    encoding   BLOB NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS enrollments (
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    PRIMARY KEY (subject_id, student_id)
);
CREATE TABLE IF NOT EXISTS class_sessions (
    id             INTEGER PRIMARY KEY,
    subject_id     INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    taken_at       TEXT NOT NULL,
    faces_detected INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS attendance (
    id         INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES class_sessions(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    status     TEXT NOT NULL CHECK (status IN ('present', 'absent')),
    method     TEXT NOT NULL CHECK (method IN ('face', 'manual')),
    confidence REAL,
    UNIQUE (session_id, student_id)
);
CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id);
CREATE INDEX IF NOT EXISTS idx_sessions_subject ON class_sessions(subject_id);
"""


class DuplicateError(Exception):
    """Raised when a unique constraint (email, subject code, roll number) is violated."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(path) if path else get_settings().db_path
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn(path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(path: str | Path | None = None) -> None:
    with get_conn(path) as conn:
        conn.executescript(SCHEMA)


# --------------------------------------------------------------------- teachers
def create_teacher(conn, name: str, email: str, password: str) -> int:
    try:
        cur = conn.execute(
            "INSERT INTO teachers (name, email, password_hash, created_at) VALUES (?,?,?,?)",
            (name.strip(), email.strip().lower(), auth.hash_password(password), _now()),
        )
    except sqlite3.IntegrityError as exc:
        raise DuplicateError("An account with this email already exists.") from exc
    return cur.lastrowid


def authenticate_teacher(conn, email: str, password: str) -> dict | None:
    row = conn.execute("SELECT * FROM teachers WHERE email = ?", (email.strip().lower(),)).fetchone()
    if row and auth.verify_password(password, row["password_hash"]):
        return {"id": row["id"], "name": row["name"], "email": row["email"]}
    return None


def get_teacher_by_email(conn, email: str) -> dict | None:
    row = conn.execute(
        "SELECT id, name, email FROM teachers WHERE email = ?", (email.strip().lower(),)
    ).fetchone()
    return dict(row) if row else None


# --------------------------------------------------------------------- subjects
def create_subject(conn, teacher_id: int, code: str, name: str) -> int:
    try:
        cur = conn.execute(
            "INSERT INTO subjects (teacher_id, code, name) VALUES (?,?,?)",
            (teacher_id, code.strip().upper(), name.strip()),
        )
    except sqlite3.IntegrityError as exc:
        raise DuplicateError(f"Subject code {code.strip().upper()} already exists.") from exc
    return cur.lastrowid


def list_subjects(conn, teacher_id: int) -> list[dict]:
    rows = conn.execute(
        """SELECT s.id, s.code, s.name,
                  (SELECT COUNT(*) FROM enrollments e WHERE e.subject_id = s.id) AS enrolled,
                  (SELECT COUNT(*) FROM class_sessions c WHERE c.subject_id = s.id) AS sessions
           FROM subjects s WHERE s.teacher_id = ? ORDER BY s.code""",
        (teacher_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def delete_subject(conn, teacher_id: int, subject_id: int) -> None:
    conn.execute("DELETE FROM subjects WHERE id = ? AND teacher_id = ?", (subject_id, teacher_id))


# --------------------------------------------------------------------- students
def create_student(
    conn,
    teacher_id: int,
    roll_no: str,
    name: str,
    email: str | None = None,
    *,
    login_id: str | None = None,
    access_code: str | None = None,
) -> dict:
    """Create a student and return their portal credentials.

    The plaintext access code is returned exactly once; only its hash is stored.
    """
    access_code = access_code or auth.generate_access_code()
    login_id = login_id or auth.generate_login_id()
    try:
        cur = conn.execute(
            """INSERT INTO students
               (teacher_id, roll_no, name, email, login_id, access_hash, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (
                teacher_id,
                roll_no.strip(),
                name.strip(),
                (email or "").strip() or None,
                login_id,
                auth.hash_password(access_code),
                _now(),
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise DuplicateError(f"Roll number {roll_no.strip()} is already enrolled.") from exc
    return {"id": cur.lastrowid, "login_id": login_id, "access_code": access_code}


def list_students(conn, teacher_id: int) -> list[dict]:
    rows = conn.execute(
        """SELECT st.id, st.roll_no, st.name, st.email, st.login_id,
                  (SELECT COUNT(*) FROM face_encodings f WHERE f.student_id = st.id) AS photos
           FROM students st WHERE st.teacher_id = ? ORDER BY st.roll_no""",
        (teacher_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def delete_student(conn, teacher_id: int, student_id: int) -> None:
    conn.execute("DELETE FROM students WHERE id = ? AND teacher_id = ?", (student_id, teacher_id))


def reset_access_code(conn, teacher_id: int, student_id: int) -> str:
    code = auth.generate_access_code()
    conn.execute(
        "UPDATE students SET access_hash = ? WHERE id = ? AND teacher_id = ?",
        (auth.hash_password(code), student_id, teacher_id),
    )
    return code


def authenticate_student(conn, login_id: str, access_code: str) -> dict | None:
    row = conn.execute("SELECT * FROM students WHERE login_id = ?", (login_id.strip().upper(),)).fetchone()
    if row and auth.verify_password(access_code.strip().upper(), row["access_hash"]):
        return {"id": row["id"], "name": row["name"], "roll_no": row["roll_no"]}
    return None


# -------------------------------------------------------------------- encodings
def add_encoding(conn, student_id: int, encoding: np.ndarray) -> None:
    blob = np.asarray(encoding, dtype=np.float64).tobytes()
    conn.execute(
        "INSERT INTO face_encodings (student_id, encoding, created_at) VALUES (?,?,?)",
        (student_id, blob, _now()),
    )


def clear_encodings(conn, student_id: int) -> None:
    conn.execute("DELETE FROM face_encodings WHERE student_id = ?", (student_id,))


def get_encodings_for_subject(conn, subject_id: int) -> dict[int, list[np.ndarray]]:
    rows = conn.execute(
        """SELECT f.student_id, f.encoding FROM face_encodings f
           JOIN enrollments e ON e.student_id = f.student_id
           WHERE e.subject_id = ?""",
        (subject_id,),
    ).fetchall()
    out: dict[int, list[np.ndarray]] = {}
    for r in rows:
        out.setdefault(r["student_id"], []).append(np.frombuffer(r["encoding"], dtype=np.float64))
    return out


# ------------------------------------------------------------------ enrollments
def set_enrollment(conn, subject_id: int, student_ids: Iterable[int]) -> None:
    """Make the subject's roster exactly `student_ids`."""
    ids = set(student_ids)
    conn.execute("DELETE FROM enrollments WHERE subject_id = ?", (subject_id,))
    conn.executemany(
        "INSERT INTO enrollments (subject_id, student_id) VALUES (?,?)",
        [(subject_id, sid) for sid in ids],
    )


def enroll(conn, subject_id: int, student_id: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO enrollments (subject_id, student_id) VALUES (?,?)",
        (subject_id, student_id),
    )


def list_enrolled(conn, subject_id: int) -> list[dict]:
    rows = conn.execute(
        """SELECT st.id, st.roll_no, st.name FROM students st
           JOIN enrollments e ON e.student_id = st.id
           WHERE e.subject_id = ? ORDER BY st.roll_no""",
        (subject_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------- attendance
def create_session(conn, subject_id: int, faces_detected: int = 0, taken_at: str | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO class_sessions (subject_id, taken_at, faces_detected) VALUES (?,?,?)",
        (subject_id, taken_at or _now(), faces_detected),
    )
    return cur.lastrowid


def save_attendance(conn, session_id: int, records: Sequence[tuple[int, str, str, float | None]]) -> None:
    """records: (student_id, 'present'|'absent', 'face'|'manual', confidence)."""
    conn.executemany(
        """INSERT OR REPLACE INTO attendance
           (session_id, student_id, status, method, confidence) VALUES (?,?,?,?,?)""",
        [(session_id, *r) for r in records],
    )
