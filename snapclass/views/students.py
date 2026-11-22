import streamlit as st

from .. import db, faces
from ..config import get_settings


def _encode_all(photos) -> tuple[list, list[str]]:
    encodings, problems = [], []
    for p in photos:
        try:
            encodings.append(faces.encode_enrolment_photo(p.getvalue(), get_settings().max_image_side))
        except ValueError as exc:
            problems.append(f"{p.name}: {exc}")
    return encodings, problems


def _enrol_form(teacher_id: int, subjects: list[dict]) -> None:
    st.caption(
        "Use 2-3 clear, front-facing, well-lit photos per student (different days or "
        "lighting work best). Only a numeric face signature is stored - never the photo."
    )
    with st.form("enrol", clear_on_submit=True):
        c1, c2, c3 = st.columns([1, 2, 2])
        roll = c1.text_input("Roll no.")
        name = c2.text_input("Full name")
        email = c3.text_input("Email (optional)")
        photos = st.file_uploader("Face photos", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        selfie = st.camera_input("...or take a photo now")
        opts = {s["id"]: f"{s['code']} - {s['name']}" for s in subjects}
        subj = st.multiselect("Enrol in subjects", list(opts), format_func=opts.get)
        submitted = st.form_submit_button("Enrol student", type="primary")

    if not submitted:
        return
    photos = list(photos) + ([selfie] if selfie else [])
    if not roll.strip() or not name.strip():
        st.error("Roll number and name are required.")
        return
    if not photos:
        st.error("Add at least one face photo.")
        return
    with st.spinner("Reading faces..."):
        encodings, problems = _encode_all(photos)
    for p in problems:
        st.warning(p)
    if not encodings:
        st.error("No usable photo - the student was not enrolled.")
        return
    try:
        with db.get_conn() as conn:
            created = db.create_student(conn, teacher_id, roll, name, email)
            for enc in encodings:
                db.add_encoding(conn, created["id"], enc)
            for sid in subj:
                db.enroll(conn, sid, created["id"])
    except db.DuplicateError as exc:
        st.error(str(exc))
        return
    st.success(f"Enrolled {name.strip()} with {len(encodings)} photo(s).")
    st.info(
        f"**Student portal login** - ID: `{created['login_id']}`  |  Access code: "
        f"`{created['access_code']}`  \nShare this now; the code is not shown again."
    )


def _manage(teacher_id: int, students: list[dict]) -> None:
    st.dataframe(
        [
            {"Roll": s["roll_no"], "Name": s["name"], "Face photos": s["photos"], "Student ID": s["login_id"]}
            for s in students
        ],
        hide_index=True,
        width="stretch",
    )
    opts = {s["id"]: f"{s['roll_no']} - {s['name']}" for s in students}
    sid = st.selectbox("Select a student", list(opts), format_func=opts.get)
    student = next(s for s in students if s["id"] == sid)

    c1, c2 = st.columns(2)
    with c1:
        more = st.file_uploader(
            "Add more face photos", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key=f"more_{sid}"
        )
        if st.button("Save photos", disabled=not more):
            encodings, problems = _encode_all(more)
            for p in problems:
                st.warning(p)
            with db.get_conn() as conn:
                for enc in encodings:
                    db.add_encoding(conn, sid, enc)
            if encodings:
                st.success(f"Added {len(encodings)} photo(s).")
                st.rerun()
    with c2:
        if st.button("Generate new access code"):
            with db.get_conn() as conn:
                code = db.reset_access_code(conn, teacher_id, sid)
            st.info(f"New access code for {student['name']}: `{code}`")
        confirm = st.checkbox("Confirm removal", key=f"rm_{sid}")
        if st.button(f"Remove {student['name']}", disabled=not confirm):
            with db.get_conn() as conn:
                db.delete_student(conn, teacher_id, sid)
            st.rerun()


def render() -> None:
    teacher = st.session_state["teacher"]
    st.title("Students")
    with db.get_conn() as conn:
        subjects = db.list_subjects(conn, teacher["id"])
        students = db.list_students(conn, teacher["id"])

    tab_enrol, tab_manage = st.tabs(["Enrol a student", f"Roster ({len(students)})"])
    with tab_enrol:
        _enrol_form(teacher["id"], subjects)
    with tab_manage:
        if students:
            _manage(teacher["id"], students)
        else:
            st.info("No students yet.")
