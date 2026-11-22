import io

import pytest

from snapclass import db


@pytest.fixture
def conn(tmp_path):
    path = tmp_path / "test.db"
    db.init_db(path)
    with db.get_conn(path) as c:
        yield c


@pytest.fixture
def teacher(conn):
    return db.create_teacher(conn, "Ms. Rao", "rao@example.com", "secret-pass1")


def png_bytes(arr) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()
