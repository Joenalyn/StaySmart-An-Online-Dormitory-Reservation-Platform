import bcrypt
from helpers import FakeCursor, FakeConnection

def _patch_mysql_connect(monkeypatch, fake_conn):
    import mysql.connector
    monkeypatch.setattr(mysql.connector, "connect", lambda **kwargs: fake_conn)

def test_login_success(monkeypatch):
    # Arrange
    cur = FakeCursor()
    pw = "Secret123!"
    hashed = bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    cur.queue_fetchone({"user_id": 7, "role": "TENANT", "password_hash": hashed})
    conn = FakeConnection(cur)

    _patch_mysql_connect(monkeypatch, conn)

    # Import after patching mysql
    from auth import Auth
    auth = Auth()

    # Act
    ok, user_id, role, msg = auth.login("shayne", pw)

    # Assert
    assert ok is True
    assert user_id == 7
    assert role == "TENANT"
    assert "successful" in msg.lower()

def test_login_invalid_password(monkeypatch):
    cur = FakeCursor()
    hashed = bcrypt.hashpw(b"CorrectPass", bcrypt.gensalt()).decode("utf-8")
    cur.queue_fetchone({"user_id": 1, "role": "OWNER", "password_hash": hashed})
    conn = FakeConnection(cur)

    _patch_mysql_connect(monkeypatch, conn)

    from auth import Auth
    auth = Auth()

    ok, user_id, role, msg = auth.login("owner1", "WrongPass")

    assert ok is False
    assert user_id is None
    assert role is None
    assert "invalid" in msg.lower()

def test_admin_signup_rejects_existing_username(monkeypatch):
    cur = FakeCursor()
    # username check returns a row => username exists
    cur.queue_fetchone({"user_id": 99})
    conn = FakeConnection(cur)

    _patch_mysql_connect(monkeypatch, conn)

    from auth import Auth
    auth = Auth()

    ok, msg = auth.admin_signup(
        fullname="Admin A",
        username="taken",
        contact="0917",
        email="a@example.com",
        password="Pass123!",
    )

    assert ok is False
    assert "username" in msg.lower()

def test_student_signup_rejects_existing_email(monkeypatch):
    cur = FakeCursor()
    # username check -> None (available)
    cur.queue_fetchone(None)
    # email check -> returns row (email exists)
    cur.queue_fetchone({"user_id": 55})
    conn = FakeConnection(cur)

    _patch_mysql_connect(monkeypatch, conn)

    from auth import Auth
    auth = Auth()

    ok, msg = auth.student_signup(
        student_name="Student S",
        username="newuser",
        contact="0999",
        email="taken@example.com",
        password="Pass123!",
    )

    assert ok is False
    assert "email" in msg.lower()
