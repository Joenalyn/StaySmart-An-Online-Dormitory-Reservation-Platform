import sys
import types

def _install_fake_mysql_connector():
    mysql_pkg = types.ModuleType("mysql")
    connector_mod = types.ModuleType("mysql.connector")

    class Error(Exception):
        pass

    def connect(*args, **kwargs):
        raise Error(
            "mysql connector not available (fake). "
            "Tests should monkeypatch mysql.connector.connect."
        )

    connector_mod.Error = Error
    connector_mod.connect = connect

    mysql_pkg.connector = connector_mod

    sys.modules.setdefault("mysql", mysql_pkg)
    sys.modules.setdefault("mysql.connector", connector_mod)

try:
    import mysql.connector
except Exception:
    _install_fake_mysql_connector()

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require real database",
    )
