from helpers import FakeCursor, FakeConnection

def _patch_mysql_connect(monkeypatch, fake_conn):
    import mysql.connector
    monkeypatch.setattr(mysql.connector, "connect", lambda **kwargs: fake_conn)

def test_get_connection_returns_none_on_error(monkeypatch):
    import mysql.connector

    def boom(**kwargs):
        raise mysql.connector.Error("no db")

    monkeypatch.setattr(mysql.connector, "connect", boom)

    from database import DatabaseManager
    db = DatabaseManager()

    assert db.get_connection() is None

def test_fetchone_returns_row_and_closes(monkeypatch):
    cur = FakeCursor()
    cur.queue_fetchone({"cnt": 3})
    conn = FakeConnection(cur)

    _patch_mysql_connect(monkeypatch, conn)

    from database import DatabaseManager
    db = DatabaseManager()

    row = db.fetchone("SELECT 1", ())

    assert row == {"cnt": 3}
    assert conn.closed is True
    assert cur.executed
    assert "SELECT" in cur.executed[0][0].upper()

def test_execute_commits_and_returns_last_id(monkeypatch):
    cur = FakeCursor()
    cur.lastrowid = 123
    conn = FakeConnection(cur)

    _patch_mysql_connect(monkeypatch, conn)

    from database import DatabaseManager
    db = DatabaseManager()

    last_id = db.execute("INSERT INTO x VALUES (%s)", (1,))

    assert last_id == 123
    assert conn.committed is True
    assert conn.closed is True

def test_mark_payment_paid_defaults_to_amount_due():
    # Avoid real DB by overriding fetchone/execute on the instance.
    from database import DatabaseManager
    db = DatabaseManager()

    calls = []
    db.fetchone = lambda sql, params=None: {"amount_due": 2500}

    def fake_execute(sql, params=None):
        calls.append((sql, params))
        return None

    db.execute = fake_execute

    ok = db.mark_payment_paid(payment_id=10, amount_paid=None)

    assert ok is True
    update_call = [c for c in calls if "UPDATE payments" in c[0]][0]
    assert update_call[1][0] == 2500  # amount_paid
    assert update_call[1][1] == 10    # payment_id

def test_get_owner_stats_occupancy_rate_calculation():
    from database import DatabaseManager
    db = DatabaseManager()

    # Dispatch based on query content.
    def fake_fetchone(sql, params=None):
        sql_norm = " ".join(sql.split()).upper()

        if "COUNT(*) AS CNT FROM DORMS" in sql_norm:
            return {"cnt": 4}
        if "FROM RENTALS" in sql_norm and "RR.STATUS" in sql_norm:
            return {"cnt": 6}
        if "FROM RENTAL_APPLICATIONS" in sql_norm and "WAITING" in sql_norm:
            return {"cnt": 2}
        if "FROM TRANSACTIONS" in sql_norm and "COALESCE(SUM(AMOUNT),0)" in sql_norm:
            return {"total": 10000}
        if "SUM(CASE WHEN STATUS='OPEN'" in sql_norm:
            return {"active_cnt": 3, "maint_cnt": 1}
        if "SUM(CAPACITY)" in sql_norm:
            return {"cap": 12}

        return None

    db.fetchone = fake_fetchone

    stats = db.get_owner_stats(owner_id=1)

    assert stats["total_dorms"] == 4
    assert stats["current_occupants"] == 6
    assert stats["pending_requests"] == 2
    assert stats["monthly_earnings"] == 10000.0
    assert stats["active_dorms"] == 3
    assert stats["maintenance_dorms"] == 1
    assert stats["occupancy_rate"] == 50  # int((6/12)*100)
