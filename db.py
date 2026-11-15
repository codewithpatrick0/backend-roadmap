"""Engine, session factory and a query counter for N+1 experiments.

    SQL_ECHO=1 uv run python my_script.py   # print every SQL statement
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://lab:lab@localhost:5433/shop")

engine = create_engine(DATABASE_URL, echo=os.environ.get("SQL_ECHO") == "1")
Session = sessionmaker(engine)


@contextmanager
def count_queries(label: str = "block") -> Iterator[dict[str, int]]:
    """Count the SQL statements sent to the database inside the `with` block."""
    counter = {"queries": 0}

    def on_execute(conn, cursor, statement, parameters, context, executemany):
        counter["queries"] += 1

    event.listen(engine, "before_cursor_execute", on_execute)
    start = time.perf_counter()
    try:
        yield counter
    finally:
        event.remove(engine, "before_cursor_execute", on_execute)
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"[{label}] {counter['queries']} queries in {elapsed_ms:.1f} ms")
