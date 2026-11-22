"""UI smoke tests: run the app and every page headlessly with Streamlit's AppTest."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from snapclass import db, demo

APP = str(Path(__file__).resolve().parents[1] / "app.py")


@pytest.fixture
def app_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SNAP_DB_PATH", str(tmp_path / "ui.db"))
    monkeypatch.setenv("SNAP_DEMO_MODE", "1")
    db.init_db()


def _app(**state) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=30)
    for k, v in state.items():
        at.session_state[k] = v
    return at.run()


def _click(at: AppTest, label: str) -> AppTest:
    return next(b for b in at.button if b.label == label).click().run()


def _view_harness(name: str, state: dict):
    """Render a single view the way app.py does, minus st.navigation."""
    import importlib

    import streamlit as st

    from snapclass.theme import apply_theme

    apply_theme()
    for k, v in state.items():
        st.session_state.setdefault(k, v)
    importlib.import_module(f"snapclass.views.{name}").render()


def _view(name: str, **state) -> AppTest:
    at = AppTest.from_function(_view_harness, args=(name, state), default_timeout=30)
    return at.run()


def test_login_page_renders(app_env):
    at = _app()
    assert not at.exception
    assert [t.label for t in at.tabs] == ["Teacher sign in", "Create teacher account", "Student portal"]


def test_registration_signs_in_new_teacher(app_env):
    at = _app()
    at.text_input(key="reg_name").set_value("New Teacher")
    at.text_input(key="reg_email").set_value("new@example.com")
    at.text_input(key="reg_pw").set_value("good-pass-1")
    at = _click(at, "Create account")
    assert not at.exception
    assert at.session_state["teacher"]["email"] == "new@example.com"
    assert at.title[0].value == "Dashboard"


def test_registration_validation(app_env):
    at = _app()
    at.text_input(key="reg_name").set_value("X")
    at.text_input(key="reg_email").set_value("not-an-email")
    at.text_input(key="reg_pw").set_value("good-pass-1")
    at = _click(at, "Create account")
    assert "valid email" in at.error[0].value
    assert "teacher" not in at.session_state


def test_bad_login_shows_error(app_env):
    at = _app()
    at.text_input(key="login_email").set_value("nobody@example.com")
    at.text_input(key="login_pw").set_value("wrong-password")
    at = _click(at, "Sign in")
    assert "Wrong email or password" in at.error[0].value


def test_demo_button_opens_populated_dashboard(app_env):
    at = _click(_app(), "Open the teacher demo")
    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Students"] == "20" and metrics["Subjects"] == "3"


def test_student_login_flow(app_env):
    with db.get_conn() as conn:
        demo.seed_demo(conn)
    at = _app()
    at.text_input(key="stu_id").set_value(demo.DEMO_STUDENT_LOGIN)
    at.text_input(key="stu_code").set_value(demo.DEMO_STUDENT_CODE)
    at = _click(at, "View my attendance")
    assert not at.exception and at.session_state["student"]["roll_no"] == "23CS001"
    assert at.metric[0].label == "Overall attendance"


@pytest.mark.parametrize("page", ["dashboard", "take_attendance", "students", "subjects", "reports"])
def test_teacher_pages_render_with_demo_data(app_env, page):
    with db.get_conn() as conn:
        tid = demo.seed_demo(conn)
    at = _view(page, teacher={"id": tid, "name": "Demo Teacher", "email": demo.DEMO_EMAIL})
    assert not at.exception, at.exception


@pytest.mark.parametrize("page", ["dashboard", "take_attendance", "students", "subjects", "reports"])
def test_teacher_pages_render_for_brand_new_account(app_env, page):
    with db.get_conn() as conn:
        tid = db.create_teacher(conn, "Fresh", "fresh@example.com", "good-pass-1")
    at = _view(page, teacher={"id": tid, "name": "Fresh", "email": "fresh@example.com"})
    assert not at.exception, at.exception
