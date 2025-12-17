from dataclasses import dataclass, field
from typing import Any, List, Tuple


@dataclass
class FakeCursor:
    dictionary: bool = False
    executed: List[Tuple[str, Any]] = field(default_factory=list)
    _fetchone_queue: List[Any] = field(default_factory=list)
    _fetchall_queue: List[Any] = field(default_factory=list)
    lastrowid: int = 0
    rowcount: int = 0

    def queue_fetchone(self, *items: Any) -> None:
        self._fetchone_queue.extend(items)

    def queue_fetchall(self, *items: Any) -> None:
        self._fetchall_queue.extend(items)

    def execute(self, sql: str, params: Any = None) -> None:
        self.executed.append((sql, params))

    def fetchone(self) -> Any:
        return self._fetchone_queue.pop(0) if self._fetchone_queue else None

    def fetchall(self) -> Any:
        return self._fetchall_queue.pop(0) if self._fetchall_queue else []


@dataclass
class FakeConnection:
    cursor_obj: FakeCursor
    committed: bool = False
    closed: bool = False
    connected: bool = True

    def is_connected(self) -> bool:
        return self.connected

    def cursor(self, dictionary: bool = False):
        self.cursor_obj.dictionary = dictionary
        return self.cursor_obj

    def commit(self) -> None:
        self.committed = True

    def close(self) -> None:
        self.closed = True
