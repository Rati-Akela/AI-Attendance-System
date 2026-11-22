"""Face detection, embedding and matching.

Pipeline: dlib HOG detector -> 5-point landmark alignment -> ResNet embedding
(128-d). Two faces are "the same person" when the Euclidean distance between
their embeddings is below a threshold. Model weights ship in the
`face-recognition-models` package and are located without importing it (it
depends on the deprecated `pkg_resources`).
"""

from __future__ import annotations

import importlib.util
import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

Box = tuple[int, int, int, int]  # left, top, right, bottom


class FaceModelError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _models():
    import dlib  # heavy import, deferred so the rest of the app loads fast

    spec = importlib.util.find_spec("face_recognition_models")
    if spec is None or not spec.submodule_search_locations:
        raise FaceModelError("Install `face-recognition-models` to enable recognition.")
    root = Path(spec.submodule_search_locations[0]) / "models"
    try:
        return (
            dlib.get_frontal_face_detector(),
            dlib.shape_predictor(str(root / "shape_predictor_5_face_landmarks.dat")),
            dlib.face_recognition_model_v1(str(root / "dlib_face_recognition_resnet_model_v1.dat")),
        )
    except RuntimeError as exc:
        raise FaceModelError(f"Could not load face models: {exc}") from exc


# ----------------------------------------------------------------------- images
def load_image(data: bytes | io.BytesIO, max_side: int = 1800) -> Image.Image:
    """Decode, honour EXIF rotation (phone photos), force RGB, cap the size."""
    img = Image.open(io.BytesIO(data) if isinstance(data, bytes) else data)
    img = ImageOps.exif_transpose(img).convert("RGB")
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return img


@dataclass
class DetectedFace:
    box: Box
    encoding: np.ndarray


def detect_faces(
    img: Image.Image, upsample: int = 1, jitters: int = 1, min_score: float = 0.25
) -> list[DetectedFace]:
    """Detect and embed faces. Detections scoring below `min_score` are dropped.

    The HOG detector occasionally fires on textured patches (flags, posters,
    clothing); its confidence score for those is far below a real face's.
    """
    detector, shaper, encoder = _models()
    arr = np.ascontiguousarray(np.asarray(img.convert("RGB"), dtype=np.uint8))
    faces: list[DetectedFace] = []
    rects, scores, _ = detector.run(arr, upsample, 0.0)
    for rect, score in zip(rects, scores, strict=True):
        if score < min_score:
            continue
        shape = shaper(arr, rect)
        enc = np.array(encoder.compute_face_descriptor(arr, shape, jitters))
        faces.append(
            DetectedFace(
                box=(max(rect.left(), 0), max(rect.top(), 0), rect.right(), rect.bottom()),
                encoding=enc,
            )
        )
    return faces


# --------------------------------------------------------------------- matching
@dataclass(frozen=True)
class Match:
    face_index: int
    student_id: int | None  # None = unrecognised
    distance: float | None


def match_score(distance: float, threshold: float) -> float:
    """Heuristic 0-100 score: 100 at distance 0, 50 at the threshold, 0 at 2x threshold."""
    return round(100 * min(max(1 - distance / (2 * threshold), 0.0), 1.0), 1)


def match_faces(
    encodings: Sequence[np.ndarray],
    known: Mapping[int, Sequence[np.ndarray]],
    threshold: float = 0.5,
) -> list[Match]:
    """Assign each detected face to at most one student, and each student to at most one face.

    A student's distance to a face is the best (smallest) over their enrolled
    photos. Candidate (face, student) pairs under the threshold are assigned
    greedily, best first, so one person can never be marked twice by a
    look-alike face and two similar students can't claim the same face.
    """
    pairs: list[tuple[float, int, int]] = []
    for fi, enc in enumerate(encodings):
        for sid, refs in known.items():
            if not len(refs):
                continue
            d = float(np.min(np.linalg.norm(np.asarray(refs) - enc, axis=1)))
            if d <= threshold:
                pairs.append((d, fi, sid))
    pairs.sort()
    taken_faces: set[int] = set()
    taken_students: set[int] = set()
    result: dict[int, Match] = {}
    for d, fi, sid in pairs:
        if fi in taken_faces or sid in taken_students:
            continue
        taken_faces.add(fi)
        taken_students.add(sid)
        result[fi] = Match(fi, sid, d)
    return [result.get(i, Match(i, None, None)) for i in range(len(encodings))]


# ------------------------------------------------------------------- annotation
_GREEN, _RED = (46, 160, 67), (220, 53, 69)


def annotate(
    img: Image.Image,
    faces: Sequence[DetectedFace],
    matches: Sequence[Match],
    names: Mapping[int, str],
) -> Image.Image:
    out = img.copy()
    draw = ImageDraw.Draw(out)
    width = max(2, out.width // 400)
    try:
        font = ImageFont.load_default(size=max(12, out.width // 60))
    except TypeError:  # very old Pillow
        font = ImageFont.load_default()
    for face, m in zip(faces, matches, strict=True):
        colour = _GREEN if m.student_id is not None else _RED
        label = names.get(m.student_id, "?") if m.student_id is not None else "Unknown"
        x0, y0, x1, y1 = face.box
        draw.rectangle((x0, y0, x1, y1), outline=colour, width=width)
        tw = draw.textlength(label, font=font)
        th = getattr(font, "size", 12) + 6
        top = max(y0 - th, 0)
        draw.rectangle((x0, top, x0 + tw + 8, top + th), fill=colour)
        draw.text((x0 + 4, top + 2), label, fill="white", font=font)
    return out


# --------------------------------------------------------------------- analysis
@dataclass
class Recognition:
    student_id: int
    distance: float
    score: float


@dataclass
class Analysis:
    images: list[Image.Image] = field(default_factory=list)  # annotated
    faces_detected: int = 0
    unknown_faces: int = 0
    recognised: dict[int, Recognition] = field(default_factory=dict)


def analyse_photos(
    photos: Sequence[bytes],
    known: Mapping[int, Sequence[np.ndarray]],
    names: Mapping[int, str],
    *,
    threshold: float = 0.5,
    max_side: int = 1800,
    upsample: int = 1,
    min_score: float = 0.25,
) -> Analysis:
    """Run recognition over one or more classroom photos and merge the results.

    Several photos let large rooms be covered from different angles; a student
    seen in more than one photo keeps their best (closest) match.
    """
    result = Analysis()
    for raw in photos:
        img = load_image(raw, max_side=max_side)
        faces = detect_faces(img, upsample=upsample, min_score=min_score)
        matches = match_faces([f.encoding for f in faces], known, threshold)
        result.images.append(annotate(img, faces, matches, names))
        result.faces_detected += len(faces)
        for m in matches:
            if m.student_id is None:
                result.unknown_faces += 1
                continue
            prev = result.recognised.get(m.student_id)
            if prev is None or m.distance < prev.distance:
                result.recognised[m.student_id] = Recognition(
                    m.student_id, m.distance, match_score(m.distance, threshold)
                )
    return result


def encode_enrolment_photo(data: bytes, max_side: int = 1800) -> np.ndarray:
    """Return the embedding for a single-person enrolment photo, or raise ValueError."""
    img = load_image(data, max_side=max_side)
    # Close-up enrolment photos should score high; be stricter than for group shots.
    faces = detect_faces(img, upsample=1, jitters=5, min_score=0.6)
    if not faces:
        raise ValueError("No face found - use a clear, front-facing, well-lit photo.")
    if len(faces) > 1:
        raise ValueError(f"{len(faces)} faces found - enrol one person per photo.")
    return faces[0].encoding
