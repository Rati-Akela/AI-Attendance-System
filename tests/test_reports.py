from snapclass import db, demo, reports


def _two_class_setup(conn, teacher):
    sub = db.create_subject(conn, teacher, "CS1", "Intro")
    a = db.create_student(conn, teacher, "R1", "Asha")["id"]
    b = db.create_student(conn, teacher, "R2", "Bala")["id"]
    db.set_enrollment(conn, sub, [a, b])
    for day, (pa, pb) in enumerate([("present", "present"), ("present", "absent")], start=1):
        s = db.create_session(conn, sub, taken_at=f"2026-03-0{day}T04:00:00+00:00")
        db.save_attendance(conn, s, [(a, pa, "face", 90.0), (b, pb, "manual", None)])
    return sub, a, b


def test_student_summary_and_risk_flag(conn, teacher):
    _two_class_setup(conn, teacher)
    df = reports.attendance_frame(conn, teacher)
    summ = reports.student_summary(df, low_pct=75).set_index("name")
    assert summ.loc["Asha", "percentage"] == 100 and not summ.loc["Asha", "at_risk"]
    assert summ.loc["Bala", "percentage"] == 50 and summ.loc["Bala", "at_risk"]


def test_session_summary(conn, teacher):
    _two_class_setup(conn, teacher)
    s = reports.session_summary(reports.attendance_frame(conn, teacher))
    assert s["present"].tolist() == [2, 1] and s["percentage"].tolist() == [100.0, 50.0]


def test_matrix_shape(conn, teacher):
    _two_class_setup(conn, teacher)
    m = reports.attendance_matrix(reports.attendance_frame(conn, teacher))
    assert m.shape == (2, 4)  # roll, name + 2 classes
    assert m[m["name"] == "Bala"].iloc[0, 2:].tolist() == ["P", "A"]


def test_timezone_conversion_changes_displayed_date(conn, teacher):
    sub = db.create_subject(conn, teacher, "CS1", "X")
    s = db.create_student(conn, teacher, "R1", "A")["id"]
    sess = db.create_session(conn, sub, taken_at="2026-03-01T22:00:00+00:00")
    db.save_attendance(conn, sess, [(s, "present", "face", 80.0)])
    utc = reports.attendance_frame(conn, teacher, tz="UTC")["date"][0]
    ist = reports.attendance_frame(conn, teacher, tz="Asia/Kolkata")["date"][0]
    assert utc == "01 Mar 2026" and ist == "02 Mar 2026"


def test_empty_data_is_safe(conn, teacher):
    df = reports.attendance_frame(conn, teacher)
    assert df.empty
    assert reports.student_summary(df).empty
    assert reports.session_summary(df).empty
    assert reports.subject_summary(df).empty
    assert reports.attendance_matrix(df).empty


def test_scoped_to_teacher(conn, teacher):
    _two_class_setup(conn, teacher)
    other = db.create_teacher(conn, "B", "b@example.com", "pass-word-1")
    assert reports.attendance_frame(conn, other).empty


def test_demo_seed_is_idempotent_and_populated(conn):
    tid = demo.seed_demo(conn)
    assert demo.seed_demo(conn) == tid
    df = reports.attendance_frame(conn, tid)
    assert df["student_id"].nunique() == 20 and df["subject_code"].nunique() == 3
    assert db.authenticate_student(conn, demo.DEMO_STUDENT_LOGIN, demo.DEMO_STUDENT_CODE)
    assert reports.subject_summary(df)["at_risk_students"].sum() > 0
