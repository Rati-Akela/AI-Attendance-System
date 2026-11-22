import streamlit as st

from .. import db, reports
from ..config import get_settings


def _csv(df) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def render() -> None:
    teacher = st.session_state["teacher"]
    cfg = get_settings()
    st.title("Reports")

    with db.get_conn() as conn:
        subjects = db.list_subjects(conn, teacher["id"])
        if not subjects:
            st.info("Nothing to report yet.")
            return
        labels = {f"{s['code']} - {s['name']}": s for s in subjects}
        subject = labels[st.selectbox("Subject", list(labels))]
        df = reports.attendance_frame(conn, teacher["id"], subject["id"], cfg.timezone)

    if df.empty:
        st.info("No attendance has been recorded for this subject yet.")
        return

    summary = reports.student_summary(df, cfg.low_attendance_pct)
    sessions = reports.session_summary(df)
    at_risk = int(summary["at_risk"].sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Classes held", len(sessions))
    c2.metric("Average attendance", f"{round(100 * df['present'].mean(), 1)}%")
    c3.metric(f"Students below {cfg.low_attendance_pct:.0f}%", at_risk)

    st.subheader("Attendance over time")
    # A real datetime axis keeps classes in chronological order (string labels sort alphabetically).
    trend = sessions.assign(when=sessions["taken_at"].dt.tz_localize(None)).set_index("when")["percentage"]
    st.line_chart(trend, y_label="% present", x_label="Class date", color="#5865F2", height=260)

    st.subheader("Per student")
    st.dataframe(
        summary,
        hide_index=True,
        width="stretch",
        column_config={
            "roll_no": "Roll",
            "name": "Student",
            "attended": "Attended",
            "total": "Classes",
            "percentage": st.column_config.ProgressColumn(
                "Attendance", min_value=0, max_value=100, format="%.1f%%"
            ),
            "at_risk": st.column_config.CheckboxColumn("At risk"),
        },
    )

    with st.expander("Class-by-class register"):
        st.dataframe(reports.attendance_matrix(df), hide_index=True, width="stretch")

    d1, d2 = st.columns(2)
    d1.download_button("Download summary (CSV)", _csv(summary), f"{subject['code']}_summary.csv", "text/csv")
    raw = df[["date", "subject_code", "roll_no", "name", "status", "method"]]
    d2.download_button(
        "Download full register (CSV)", _csv(raw), f"{subject['code']}_register.csv", "text/csv"
    )
