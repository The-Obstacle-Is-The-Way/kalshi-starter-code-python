from __future__ import annotations

import sqlite3

import pytest
from alembic import command
from alembic.config import Config

pytestmark = [pytest.mark.integration]


def _tables(db_path) -> set[str]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {r[0] for r in rows}


def test_alembic_upgrade_downgrade_roundtrip(tmp_path) -> None:
    db_path = tmp_path / "alembic_test.db"
    url = f"sqlite+aiosqlite:///{db_path}"

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)

    command.upgrade(cfg, "head")
    tables_after_upgrade = _tables(db_path)
    for table in ("events", "markets", "price_snapshots", "settlements", "positions", "trades"):
        assert table in tables_after_upgrade

    command.downgrade(cfg, "base")
    tables_after_downgrade = _tables(db_path)
    for table in ("events", "markets", "price_snapshots", "settlements", "positions", "trades"):
        assert table not in tables_after_downgrade

    command.upgrade(cfg, "head")
    tables_after_reupgrade = _tables(db_path)
    for table in ("events", "markets", "price_snapshots", "settlements", "positions", "trades"):
        assert table in tables_after_reupgrade
