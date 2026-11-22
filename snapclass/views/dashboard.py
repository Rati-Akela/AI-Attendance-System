import streamlit as st

from .. import db, reports
from ..config import get_settings


def render() -> None:
    teacher = st.session_state["teacher"]
    cfg = get_settings()
    st.title("Dashboard")
    st.caption(f"Welcome back, {teacher['name']}.")

    with db.get_conn() as conn:
        subjects = db.list_subjects(conn, teacher["id"])
        students = db.list_students(conn, teacher["id"])
        df = reports.attendance_frame(conn, teacher["id"], tz=cfg.timezone)

    if not subjects:
        st.info(
            "Get started: add a subject in **Subjects**, enrol students with a clear photo "
            "in **Students**, then use **Take attendance**."
        )
        c1, c2 = st.columns(2)
        c1.metric("Subjects", 0)
        c2.metric("Students", len(students))
        return

    sessions = reports.session_summary(df)
    summary = reports.student_summary(df, cfg.low_attendance_pct)
    overall = round(100 * df["present"].mean(), 1) if not df.empty else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Subjects", len(subjects))
    c2.metric("Students", len(students))
    c3.metric("Classes held", int(df["session_id"].nunique()) if not df.empty else 0)
    c4.metric("Avg. attendance", f"{overall}%" if overall is not None else "-")

    if df.empty:
        st.info("No attendance recorded yet - head to **Take attendance**.")
        return

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Attendance by subject")
        subj = reports.subject_summary(df, cfg.low_attendance_pct)
        st.bar_chart(
            subj.set_index("subject_code")["avg_attendance"], y_label="% present", color="#5865F2", height=280
        )
    with right:
        st.subheader(f"Below {cfg.low_attendance_pct:.0f}%")
        # Across all subjects, a student's overall percentage.
        risk = summary[summary["at_risk"]].sort_values("percentage")
        if risk.empty:
            st.success("Nobody is below the threshold.")
        else:
            st.dataframe(
                risk[["roll_no", "name", "percentage"]],
                hide_index=True,
                width="stretch",
                column_config={
                    "roll_no": "Roll",
                    "name": "Student",
                    "percentage": st.column_config.NumberColumn("%", format="%.1f"),
                },
            )

    st.subheader("Recent classes")
    recent = (
        df.drop_duplicates("session_id")[["session_id", "subject_code"]]
        .merge(sessions, on="session_id")
        .sort_values("taken_at", ascending=False)
        .head(8)
    )
    st.dataframe(
        recent[["date", "subject_code", "present", "total", "percentage"]],
        hide_index=True,
        width="stretch",
        column_config={
            "date": "Date",
            "subject_code": "Subject",
            "present": "Present",
            "total": "Enrolled",
            "percentage": st.column_config.ProgressColumn(
                "Attendance", min_value=0, max_value=100, format="%.0f%%"
            ),
        },
    )
