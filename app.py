"""SNAP CLASS - entry point.   Run with:  streamlit run app.py"""

import streamlit as st

from snapclass import db
from snapclass.theme import apply_theme
from snapclass.views import dashboard, login, reports, student_portal, students, subjects, take_attendance

st.set_page_config(page_title="SNAP CLASS", page_icon=":material/photo_camera:", layout="wide")
apply_theme()
db.init_db()


def _sign_out() -> None:
    for key in ("teacher", "student", "pending"):
        st.session_state.pop(key, None)
    st.rerun()


if "teacher" in st.session_state:
    pages = [
        st.Page(
            dashboard.render,
            title="Dashboard",
            icon=":material/dashboard:",
            url_path="dashboard",
            default=True,
        ),
        st.Page(
            take_attendance.render,
            title="Take attendance",
            icon=":material/photo_camera:",
            url_path="attendance",
        ),
        st.Page(students.render, title="Students", icon=":material/group:", url_path="students"),
        st.Page(subjects.render, title="Subjects", icon=":material/menu_book:", url_path="subjects"),
        st.Page(reports.render, title="Reports", icon=":material/bar_chart:", url_path="reports"),
    ]
    who = st.session_state["teacher"]["name"]
elif "student" in st.session_state:
    pages = [
        st.Page(student_portal.render, title="My attendance", icon=":material/fact_check:", url_path="me")
    ]
    who = st.session_state["student"]["name"]
else:
    pages = [st.Page(login.render, title="Sign in", icon=":material/login:")]
    who = None

nav = st.navigation(pages, position="sidebar" if who else "hidden")
if who:
    with st.sidebar:
        st.caption(f"Signed in as **{who}**")
        if st.button("Sign out", width="stretch"):
            _sign_out()
nav.run()
