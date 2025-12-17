import pytest
from database import DatabaseManager


@pytest.mark.integration
def test_database_connection_works():
    """
    Verifies that the application can connect to the real database.
    """
    db = DatabaseManager()
    conn = db.get_connection()
    assert conn is not None
    conn.close()


@pytest.mark.integration
def test_fetch_owner_stats_executes_end_to_end():
    """
    Runs a real end-to-end query path without asserting specific values.
    """
    db = DatabaseManager()
    stats = db.get_owner_stats(owner_id=1)

    assert isinstance(stats, dict)
    assert "total_dorms" in stats
    assert "occupancy_rate" in stats


@pytest.mark.integration
def test_simple_insert_and_select_user():
    """
    Integration test for INSERT + SELECT using the real database.
    Uses a unique username to avoid collisions.
    """
    import uuid

    db = DatabaseManager()  # ✅ MISSING LINE FIXED

    username = f"integration_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"

    user_id = db.create_user(
        role="TEST",
        fullname="Integration Test",
        username=username,
        email=email,
        contact_no="0000",
        password_hash="hash"
    )

    assert user_id is not None

    user = db.get_user_by_username(username)
    assert user is not None
    assert user["email"] == email


@pytest.mark.integration
def test_fetch_all_rooms_runs():
    """
    Simple integration test to ensure a SELECT query executes.
    """
    db = DatabaseManager()
    rooms = db.get_all_rooms()
    assert isinstance(rooms, list)


@pytest.mark.integration
def test_get_recommended_rooms_runs():
    """
    Ensures recommendation query executes against real DB.
    """
    db = DatabaseManager()
    rooms = db.get_recommended_rooms(limit=3)
    assert isinstance(rooms, list)
