"""Landing page: teacher sign-in / registration and the student portal sign-in."""

import streamlit as st

from .. import auth, db, demo
from ..config import get_settings


def _teacher_login():
    with st.form("teacher_login"):
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pw")
        if st.form_submit_button("Sign in", type="primary"):
            with db.get_conn() as conn:
                teacher = db.authenticate_teacher(conn, email, password)
            if teacher:
                st.session_state["teacher"] = teacher
                st.rerun()
            st.error("Wrong email or password.")


def _register():
    with st.form("register"):
        name = st.text_input("Full name", key="reg_name")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input(
            "Password",
            type="password",
            key="reg_pw",
            help="At least 8 characters, mixing letters and numbers.",
        )
        if st.form_submit_button("Create account", type="primary"):
            if not name.strip():
                st.error("Please enter your name.")
            elif not auth.validate_email(email):
                st.error("Please enter a valid email address.")
            elif problem := auth.validate_password(password):
                st.error(problem)
            else:
                try:
                    with db.get_conn() as conn:
                        tid = db.create_teacher(conn, name, email, password)
                except db.DuplicateError as exc:
                    st.error(str(exc))
                else:
                    st.session_state["teacher"] = {
                        "id": tid,
                        "name": name.strip(),
                        "email": email.strip().lower(),
                    }
                    st.rerun()


def _student_login():
    st.caption("Your teacher gives you a Student ID and access code when you are enrolled.")
    with st.form("student_login"):
        login_id = st.text_input("Student ID", placeholder="SC-XXXXXX", key="stu_id")
        code = st.text_input("Access code", type="password", key="stu_code")
        if st.form_submit_button("View my attendance", type="primary"):
            with db.get_conn() as conn:
                student = db.authenticate_student(conn, login_id, code)
            if student:
                st.session_state["student"] = student
                st.rerun()
            st.error("Student ID or access code is incorrect.")


def render() -> None:
    st.title("SNAP CLASS")
    st.markdown(
        '<p class="snap-hero">Attendance in one photo. Upload a class picture and '
        "AI marks who is present.</p>",
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["Teacher sign in", "Create teacher account", "Student portal"])
    with tabs[0]:
        _teacher_login()
    with tabs[1]:
        _register()
    with tabs[2]:
        _student_login()

    if get_settings().demo_mode:
        st.divider()
        st.subheader("Just looking?")
        st.write("Explore a fully populated demo classroom - no sign-up needed.")
        c1, c2 = st.columns(2)
        if c1.button("Open the teacher demo", type="primary"):
            with db.get_conn() as conn:
                tid = demo.seed_demo(conn)
            st.session_state["teacher"] = {"id": tid, "name": "Demo Teacher", "email": demo.DEMO_EMAIL}
            st.rerun()
        c2.caption(
            f"Student portal demo: ID `{demo.DEMO_STUDENT_LOGIN}`, code `{demo.DEMO_STUDENT_CODE}` "
            "(load the teacher demo once first)."
        )
