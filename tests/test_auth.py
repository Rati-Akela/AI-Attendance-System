from snapclass import auth


def test_hash_roundtrip_and_salting():
    h1, h2 = auth.hash_password("hunter2-pass"), auth.hash_password("hunter2-pass")
    assert h1 != h2  # unique salts
    assert auth.verify_password("hunter2-pass", h1)
    assert not auth.verify_password("wrong", h1)


def test_verify_rejects_malformed_hash():
    assert not auth.verify_password("x", "not-a-hash")
    assert not auth.verify_password("x", "md5$1$aa$bb")


def test_password_rules():
    assert auth.validate_password("short1") is not None
    assert auth.validate_password("onlyletters") is not None
    assert auth.validate_password("12345678") is not None
    assert auth.validate_password("good-pass-1") is None


def test_email_validation():
    assert auth.validate_email("a@b.co")
    assert not auth.validate_email("nope")
    assert not auth.validate_email("a b@c.com")


def test_generated_codes_are_unambiguous():
    code = auth.generate_access_code()
    assert len(code) == 8 and not set(code) & set("0O1IL")
    assert auth.generate_login_id().startswith("SC-")
