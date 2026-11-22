"""Attendance analytics built on pandas."""

from __future__ import annotations

import pandas as pd

_COLUMNS = [
    "session_id",
    "subject_id",
    "subject_code",
    "subject_name",
    "taken_at",
    "student_id",
    "roll_no",
    "name",
    "status",
    "method",
    "confidence",
]

_BASE_SQL = """
SELECT a.session_id, sub.id AS subject_id, sub.code AS subject_code,
       sub.name AS subject_name, s.taken_at, st.id AS student_id, st.roll_no,
       st.name, a.status, a.method, a.confidence
FROM attendance a
JOIN class_sessions s ON s.id = a.session_id
JOIN subjects sub     ON sub.id = s.subject_id
JOIN students st      ON st.id = a.student_id
"""


def _finish(df: pd.DataFrame, tz: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=_COLUMNS + ["date"])
    df["taken_at"] = pd.to_datetime(df["taken_at"], utc=True).dt.tz_convert(tz)
    df["date"] = df["taken_at"].dt.strftime("%d %b %Y")
    df["present"] = (df["status"] == "present").astype(int)
    return df.sort_values(["taken_at", "roll_no"]).reset_index(drop=True)


def attendance_frame(conn, teacher_id: int, subject_id: int | None = None, tz: str = "UTC") -> pd.DataFrame:
    sql = _BASE_SQL + " WHERE sub.teacher_id = ?"
    params: list = [teacher_id]
    if subject_id is not None:
        sql += " AND sub.id = ?"
        params.append(subject_id)
    return _finish(pd.read_sql_query(sql, conn, params=params), tz)


def student_frame(conn, student_id: int, tz: str = "UTC") -> pd.DataFrame:
    return _finish(pd.read_sql_query(_BASE_SQL + " WHERE st.id = ?", conn, params=[student_id]), tz)


def student_summary(df: pd.DataFrame, low_pct: float = 75.0) -> pd.DataFrame:
    """Per-student attended / total / percentage, flagged when below `low_pct`."""
    cols = ["roll_no", "name", "attended", "total", "percentage", "at_risk"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    g = df.groupby(["student_id", "roll_no", "name"], as_index=False).agg(
        attended=("present", "sum"), total=("present", "count")
    )
    g["percentage"] = (100 * g["attended"] / g["total"]).round(1)
    g["at_risk"] = g["percentage"] < low_pct
    return g.sort_values("roll_no")[cols].reset_index(drop=True)


def subject_summary(df: pd.DataFrame, low_pct: float = 75.0) -> pd.DataFrame:
    """Per-subject class count, average attendance and number of at-risk students."""
    cols = ["subject_code", "subject_name", "classes", "avg_attendance", "at_risk_students"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for (code, name), sub in df.groupby(["subject_code", "subject_name"]):
        stu = student_summary(sub, low_pct)
        rows.append(
            {
                "subject_code": code,
                "subject_name": name,
                "classes": sub["session_id"].nunique(),
                "avg_attendance": round(100 * sub["present"].mean(), 1),
                "at_risk_students": int(stu["at_risk"].sum()),
            }
        )
    return pd.DataFrame(rows, columns=cols)


def session_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per class: how many were present and the percentage."""
    cols = ["session_id", "taken_at", "date", "present", "total", "percentage"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    g = df.groupby("session_id", as_index=False).agg(
        taken_at=("taken_at", "first"),
        date=("date", "first"),
        present=("present", "sum"),
        total=("present", "count"),
    )
    g["percentage"] = (100 * g["present"] / g["total"]).round(1)
    return g.sort_values("taken_at")[cols].reset_index(drop=True)


def attendance_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Students x classes grid of P / A, for a quick visual scan."""
    if df.empty:
        return pd.DataFrame()
    d = df.assign(
        mark=df["present"].map({1: "P", 0: "A"}),
        col=df["taken_at"].dt.strftime("%d %b %H:%M"),
    )
    m = d.pivot_table(index=["roll_no", "name"], columns="col", values="mark", aggfunc="first")
    order = d.drop_duplicates("col").sort_values("taken_at")["col"].tolist()
    return m[order].reset_index()
