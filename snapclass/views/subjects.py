import streamlit as st

from .. import db


def render() -> None:
    teacher = st.session_state["teacher"]
    st.title("Subjects")

    with st.expander("Add a subject", expanded=not st.session_state.get("_has_subjects", False)):
        with st.form("add_subject", clear_on_submit=True):
            c1, c2 = st.columns([1, 2])
            code = c1.text_input("Code", placeholder="CS301")
            name = c2.text_input("Name", placeholder="Machine Learning")
            if st.form_submit_button("Add subject", type="primary"):
                if not code.strip() or not name.strip():
                    st.error("Both code and name are required.")
                else:
                    try:
                        with db.get_conn() as conn:
                            db.create_subject(conn, teacher["id"], code, name)
                        st.success(f"Added {code.strip().upper()}.")
                    except db.DuplicateError as exc:
                        st.error(str(exc))

    with db.get_conn() as conn:
        subjects = db.list_subjects(conn, teacher["id"])
        students = db.list_students(conn, teacher["id"])
    st.session_state["_has_subjects"] = bool(subjects)

    if not subjects:
        st.info("No subjects yet.")
        return

    st.dataframe(
        [
            {"Code": s["code"], "Name": s["name"], "Students": s["enrolled"], "Classes": s["sessions"]}
            for s in subjects
        ],
        hide_index=True,
        width="stretch",
    )

    st.subheader("Manage a subject")
    labels = {f"{s['code']} - {s['name']}": s for s in subjects}
    subject = labels[st.selectbox("Subject", list(labels))]

    with db.get_conn() as conn:
        current = {r["id"] for r in db.list_enrolled(conn, subject["id"])}

    if not students:
        st.info("Add students first (Students page), then enrol them here.")
    else:
        options = {s["id"]: f"{s['roll_no']} - {s['name']}" for s in students}
        chosen = st.multiselect(
            "Enrolled students",
            list(options),
            default=sorted(current),
            format_func=options.get,
            key=f"roster_{subject['id']}",
        )
        if st.button("Save roster"):
            with db.get_conn() as conn:
                db.set_enrollment(conn, subject["id"], chosen)
            st.success("Roster updated.")
            st.rerun()

    with st.expander("Danger zone"):
        st.warning(f"Deleting {subject['code']} also deletes all of its attendance records.")
        confirm = st.checkbox(f"Yes, delete {subject['code']}", key=f"del_{subject['id']}")
        if st.button("Delete subject", disabled=not confirm):
            with db.get_conn() as conn:
                db.delete_subject(conn, teacher["id"], subject["id"])
            st.rerun()
