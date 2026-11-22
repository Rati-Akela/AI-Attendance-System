import numpy as np
import pytest

from snapclass import faces

from .conftest import png_bytes


def vec(seed: int, noise: float = 0.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    base = rng.normal(size=128)
    base /= np.linalg.norm(base)
    return base + (rng.normal(scale=noise, size=128) if noise else 0)


# ---------------------------------------------------------------- pure matching
def test_matches_correct_student():
    known = {1: [vec(1)], 2: [vec(2)]}
    res = faces.match_faces([vec(2, 0.01), vec(1, 0.01)], known, threshold=0.5)
    assert [m.student_id for m in res] == [2, 1]


def test_unknown_face_is_unmatched():
    res = faces.match_faces([vec(99)], {1: [vec(1)]}, threshold=0.5)
    assert res[0].student_id is None and res[0].distance is None


def test_student_matched_to_best_face_only():
    """Two look-alike faces: the student is claimed once, by the closer face."""
    known = {1: [vec(1)]}
    close, far = vec(1, 0.005), vec(1, 0.02)
    res = faces.match_faces([far, close], known, threshold=0.9)
    assert res[1].student_id == 1
    assert res[0].student_id is None


def test_uses_best_of_multiple_reference_photos():
    known = {1: [vec(50), vec(1)]}
    assert faces.match_faces([vec(1, 0.01)], known)[0].student_id == 1


def test_threshold_is_respected():
    known = {1: [vec(1)]}
    probe = vec(1, 0.05)
    d = float(np.linalg.norm(probe - known[1][0]))
    assert faces.match_faces([probe], known, threshold=d + 0.01)[0].student_id == 1
    assert faces.match_faces([probe], known, threshold=d - 0.01)[0].student_id is None


def test_empty_inputs():
    assert faces.match_faces([], {1: [vec(1)]}) == []
    assert faces.match_faces([vec(1)], {})[0].student_id is None
    assert faces.match_faces([vec(1)], {1: []})[0].student_id is None


def test_match_score_bounds():
    assert faces.match_score(0, 0.5) == 100
    assert faces.match_score(0.5, 0.5) == 50
    assert faces.match_score(5, 0.5) == 0


# ------------------------------------------------- real model, real face photo
@pytest.fixture(scope="module")
def astronaut():
    skimage_data = pytest.importorskip("skimage.data")
    return skimage_data.astronaut()  # 512x512 RGB with one clear face


@pytest.fixture(scope="module")
def models_available():
    try:
        faces._models()
    except (ImportError, faces.FaceModelError, OSError, RuntimeError) as exc:  # dlib or weights missing
        pytest.skip(f"face models unavailable: {exc}")


def test_enrolment_photo_yields_128d_embedding(astronaut, models_available):
    enc = faces.encode_enrolment_photo(png_bytes(astronaut))
    assert enc.shape == (128,)


def test_enrolment_rejects_photo_without_face(models_available):
    blank = np.full((300, 300, 3), 128, dtype=np.uint8)
    with pytest.raises(ValueError, match="No face"):
        faces.encode_enrolment_photo(png_bytes(blank))


def test_enrolment_rejects_group_photo(astronaut, models_available):
    two = np.concatenate([astronaut, astronaut], axis=1)
    with pytest.raises(ValueError, match="2 faces"):
        faces.encode_enrolment_photo(png_bytes(two))


def test_end_to_end_recognition(astronaut, models_available):
    enc = faces.encode_enrolment_photo(png_bytes(astronaut))
    known = {7: [enc], 8: [vec(8)]}
    result = faces.analyse_photos([png_bytes(astronaut)], known, {7: "Eileen", 8: "Other"}, threshold=0.5)
    assert result.faces_detected == 1
    assert list(result.recognised) == [7]
    assert result.recognised[7].score > 80
    assert result.unknown_faces == 0
    assert result.images[0].size == astronaut.shape[1::-1]


def test_same_person_twice_counts_once_and_other_face_is_unknown(astronaut, models_available):
    enc = faces.encode_enrolment_photo(png_bytes(astronaut))
    two = np.concatenate([astronaut, astronaut], axis=1)
    result = faces.analyse_photos([png_bytes(two)], {7: [enc]}, {7: "E"})
    assert result.faces_detected == 2
    assert set(result.recognised) == {7}
    assert result.unknown_faces == 1


def test_exif_rotation_and_downscale(astronaut):
    img = faces.load_image(png_bytes(astronaut), max_side=256)
    assert max(img.size) == 256 and img.mode == "RGB"


def test_low_confidence_detection_is_filtered(astronaut, models_available):
    from PIL import Image

    img = Image.fromarray(astronaut)
    assert len(faces.detect_faces(img, upsample=1, min_score=0.0)) == 2  # includes a false positive
    assert len(faces.detect_faces(img, upsample=1)) == 1
