import pandas as pd
import streamlit as st

from .. import db, faces
from ..config import get_settings


def _analyse(photos: list[bytes], known, enrolled, cfg):
    names = {s["id"]: s["name"] for s in enrolled}
    return faces.analyse_photos(
        photos,
        known,
        names,
        threshold=cfg.match_threshold,
        max_side=cfg.max_image_side,
        upsample=cfg.upsample,
        min_score=cfg.min_face_score,
    )


def _review(subject: dict, enrolled: list[dict], pending: dict) -> None:
    result = pending["result"]
    n_known = len(result.recognised)

    c1, c2, c3 = st.columns(3)
    c1.metric("Faces detected", result.faces_detected)
    c2.metric("Students recognised", f"{n_known} / {len(enrolled)}")
    c3.metric("Unrecognised faces", result.unknown_faces)

    for img in result.images:
        st.image(img, width="stretch")
    if result.unknown_faces:
        st.caption(
            "Red boxes are faces that matched nobody on this roster (visitors, students not "
            "enrolled in this subject, or poor angles). Tick students manually below if needed."
        )

    st.subheader("Review and confirm")
    rows = []
    for s in enrolled:
        rec = result.recognised.get(s["id"])
        rows.append(
            {
                "student_id": s["id"],
                "Present": rec is not None,
                "Roll": s["roll_no"],
                "Name": s["name"],
                "Match score": rec.score if rec else None,
            }
        )
    edited = st.data_editor(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        key=f"review_{pending['key']}",
        disabled=["Roll", "Name", "Match score"],
        column_config={"student_id": None, "Match score": st.column_config.NumberColumn(format="%.0f")},
    )

    if st.button("Save attendance", type="primary"):
        records = []
        for _, row in edited.iterrows():
            sid = int(row["student_id"])
            rec = result.recognised.get(sid)
            present = bool(row["Present"])
            auto = rec is not None and present  # untouched face match
            records.append(
                (
                    sid,
                    "present" if present else "absent",
                    "face" if auto else "manual",
                    rec.score if auto else None,
                )
            )
        with db.get_conn() as conn:
            session_id = db.create_session(conn, subject["id"], result.faces_detected)
            db.save_attendance(conn, session_id, records)
        st.session_state.pop("pending", None)
        st.success(
            f"Saved: {sum(r[1] == 'present' for r in records)} present, "
            f"{sum(r[1] == 'absent' for r in records)} absent."
        )
        st.balloons()


def render() -> None:
    teacher = st.session_state["teacher"]
    cfg = get_settings()
    st.title("Take attendance")

    with db.get_conn() as conn:
        subjects = db.list_subjects(conn, teacher["id"])
    if not subjects:
        st.info("Create a subject first.")
        return
    labels = {f"{s['code']} - {s['name']}": s for s in subjects}
    subject = labels[st.selectbox("Subject", list(labels))]

    with db.get_conn() as conn:
        enrolled = db.list_enrolled(conn, subject["id"])
        known = db.get_encodings_for_subject(conn, subject["id"])
    if not enrolled:
        st.info("No students are enrolled in this subject yet (see Subjects -> Manage).")
        return
    missing = [s["name"] for s in enrolled if s["id"] not in known]
    if len(missing) == len(enrolled):
        st.error(
            "None of the enrolled students have face photos, so nobody can be recognised. "
            "Add photos on the Students page - or mark everyone manually below."
        )
    elif missing:
        st.warning(f"No face photo on file for: {', '.join(missing)}. They will need to be ticked manually.")

    up, cam = st.tabs(["Upload photo(s)", "Use camera"])
    with up:
        files = st.file_uploader(
            "Class photo(s) - add several angles for big rooms",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
        )
    with cam:
        shot = st.camera_input("Take the class photo")
    photos = [f.getvalue() for f in files] + ([shot.getvalue()] if shot else [])

    if st.button("Recognise faces", type="primary", disabled=not photos):
        with st.spinner("Detecting and matching faces..."):
            try:
                result = _analyse(photos, known, enrolled, cfg)
            except faces.FaceModelError as exc:
                st.error(str(exc))
                return
        st.session_state["pending"] = {
            "subject_id": subject["id"],
            "result": result,
            "key": hash(tuple(photos)),
        }

    pending = st.session_state.get("pending")
    if pending and pending["subject_id"] == subject["id"]:
        _review(subject, enrolled, pending)
    elif not photos:
        st.caption("Tip: take the photo from the front of the room with faces at least ~80 px wide.")
