"""Integration: enrol a real face -> recognise it in a class photo -> save -> report."""

import numpy as np
import pytest

from snapclass import db, faces, reports

from .conftest import png_bytes


@pytest.fixture(scope="module")
def astronaut():
    return pytest.importorskip("skimage.data").astronaut()


def test_full_attendance_flow(conn, teacher, astronaut):
    try:
        faces._models()
    except (ImportError, faces.FaceModelError, OSError, RuntimeError) as exc:
        pytest.skip(f"face models unavailable: {exc}")

    subject = db.create_subject(conn, teacher, "CS1", "Intro")
    eileen = db.create_student(conn, teacher, "R1", "Eileen")["id"]
    absent = db.create_student(conn, teacher, "R2", "Someone Else")["id"]
    db.add_encoding(conn, eileen, faces.encode_enrolment_photo(png_bytes(astronaut)))
    db.add_encoding(conn, absent, np.random.default_rng(3).normal(size=128))
    db.set_enrollment(conn, subject, [eileen, absent])

    known = db.get_encodings_for_subject(conn, subject)
    names = {s["id"]: s["name"] for s in db.list_enrolled(conn, subject)}
    result = faces.analyse_photos([png_bytes(astronaut)], known, names)
    assert set(result.recognised) == {eileen}

    session = db.create_session(conn, subject, result.faces_detected)
    db.save_attendance(
        conn,
        session,
        [(sid, "present" if sid in result.recognised else "absent", "face", None) for sid in names],
    )
    summary = reports.student_summary(reports.attendance_frame(conn, teacher)).set_index("name")
    assert summary.loc["Eileen", "percentage"] == 100
    assert summary.loc["Someone Else", "percentage"] == 0
