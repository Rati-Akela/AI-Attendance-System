import streamlit as st

from .. import db, reports
from ..config import get_settings


def render() -> None:
    student = st.session_state["student"]
    cfg = get_settings()
    st.title(f"Hi, {student['name'].split()[0]}")
    st.caption(f"Roll no. {student['roll_no']}")

    with db.get_conn() as conn:
        df = reports.student_frame(conn, student["id"], cfg.timezone)
    if df.empty:
        st.info("No attendance has been recorded for you yet.")
        return

    overall = 100 * df["present"].mean()
    st.metric("Overall attendance", f"{overall:.1f}%")
    if overall < cfg.low_attendance_pct:
        st.warning(f"Your attendance is below the {cfg.low_attendance_pct:.0f}% requirement.")

    st.subheader("By subject")
    for (code, name), sub in df.groupby(["subject_code", "subject_name"]):
        pct = 100 * sub["present"].mean()
        st.write(f"**{code} - {name}**  ·  {int(sub['present'].sum())}/{len(sub)} classes ({pct:.0f}%)")
        st.progress(min(pct / 100, 1.0))

    st.subheader("Recent classes")
    recent = df.sort_values("taken_at", ascending=False).head(15)
    st.dataframe(
        recent[["date", "subject_code", "status"]].rename(
            columns={"date": "Date", "subject_code": "Subject", "status": "Status"}
        ),
        hide_index=True,
        width="stretch",
    )
