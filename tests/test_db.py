import numpy as np
import pytest

from snapclass import db


def test_teacher_signup_and_login(conn):
    db.create_teacher(conn, "A", "A@Example.com", "pass-word-1")
    assert db.authenticate_teacher(conn, "a@example.com", "pass-word-1")["name"] == "A"
    assert db.authenticate_teacher(conn, "a@example.com", "bad") is None
    with pytest.raises(db.DuplicateError):
        db.create_teacher(conn, "B", "a@example.com", "other-pass-1")


def test_subject_codes_unique_per_teacher(conn, teacher):
    db.create_subject(conn, teacher, "cs101", "Intro")
    assert db.list_subjects(conn, teacher)[0]["code"] == "CS101"
    with pytest.raises(db.DuplicateError):
        db.create_subject(conn, teacher, "CS101", "Again")
    other = db.create_teacher(conn, "B", "b@example.com", "pass-word-1")
    db.create_subject(conn, other, "CS101", "Same code, other teacher")  # allowed


def test_student_portal_credentials(conn, teacher):
    s = db.create_student(conn, teacher, "R1", "Asha")
    assert db.authenticate_student(conn, s["login_id"].lower(), s["access_code"].lower())
    assert db.authenticate_student(conn, s["login_id"], "WRONGCODE") is None
    new = db.reset_access_code(conn, teacher, s["id"])
    assert db.authenticate_student(conn, s["login_id"], s["access_code"]) is None
    assert db.authenticate_student(conn, s["login_id"], new)


def test_duplicate_roll_number(conn, teacher):
    db.create_student(conn, teacher, "R1", "Asha")
    with pytest.raises(db.DuplicateError):
        db.create_student(conn, teacher, "R1", "Someone else")


def test_encodings_only_returned_for_enrolled_students(conn, teacher):
    sub = db.create_subject(conn, teacher, "CS1", "X")
    a = db.create_student(conn, teacher, "R1", "A")["id"]
    b = db.create_student(conn, teacher, "R2", "B")["id"]
    for sid in (a, b):
        db.add_encoding(conn, sid, np.full(128, sid, dtype=float))
    db.set_enrollment(conn, sub, [a])
    known = db.get_encodings_for_subject(conn, sub)
    assert list(known) == [a]
    assert known[a][0].shape == (128,)
    db.set_enrollment(conn, sub, [a, b])
    assert set(db.get_encodings_for_subject(conn, sub)) == {a, b}


def test_deleting_student_cascades(conn, teacher):
    sub = db.create_subject(conn, teacher, "CS1", "X")
    s = db.create_student(conn, teacher, "R1", "A")["id"]
    db.set_enrollment(conn, sub, [s])
    db.add_encoding(conn, s, np.zeros(128))
    sess = db.create_session(conn, sub)
    db.save_attendance(conn, sess, [(s, "present", "face", 90.0)])
    db.delete_student(conn, teacher, s)
    for table in ("enrollments", "face_encodings", "attendance"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_teachers_cannot_delete_each_others_data(conn, teacher):
    other = db.create_teacher(conn, "B", "b@example.com", "pass-word-1")
    sub = db.create_subject(conn, teacher, "CS1", "X")
    db.delete_subject(conn, other, sub)
    assert len(db.list_subjects(conn, teacher)) == 1


def test_resaving_attendance_overwrites(conn, teacher):
    sub = db.create_subject(conn, teacher, "CS1", "X")
    s = db.create_student(conn, teacher, "R1", "A")["id"]
    sess = db.create_session(conn, sub)
    db.save_attendance(conn, sess, [(s, "absent", "face", None)])
    db.save_attendance(conn, sess, [(s, "present", "manual", None)])
    rows = conn.execute("SELECT status, method FROM attendance").fetchall()
    assert [tuple(r) for r in rows] == [("present", "manual")]
