"""Shared helper functions for data CLI commands."""

from pathlib import Path


def find_alembic_ini() -> Path:
    """Locate the alembic.ini configuration file.

    Searches the current directory first, then walks up the directory tree
    from this file's location.

    Returns:
        Path to the alembic.ini file.

    Raises:
        FileNotFoundError: If alembic.ini cannot be found.
    """
    alembic_ini = Path("alembic.ini")
    if alembic_ini.exists():
        return alembic_ini

    for parent in Path(__file__).resolve().parents:
        candidate = parent / "alembic.ini"
        if candidate.exists():
            return candidate

    raise FileNotFoundError("alembic.ini not found")


def validate_migrations_on_temp_db(*, alembic_ini: Path, db_path: Path) -> None:
    """Validate Alembic migrations by running them against a temporary DB copy.

    Args:
        alembic_ini: Path to the alembic.ini configuration file.
        db_path: Path to the local SQLite database file.
    """
    import shutil
    import tempfile

    from alembic import command
    from alembic.config import Config

    db_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        suffix=".db",
        prefix="kalshi-migrate-",
        dir=str(db_path.parent),
        delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)

    try:
        if db_path.exists():
            shutil.copy2(db_path, tmp_path)
        else:
            tmp_path.touch()

        tmp_cfg = Config(str(alembic_ini))
        # Alembic is invoked synchronously, but our alembic `env.py` runs migrations via
        # `async_engine_from_config`, so the async driver URL is required here.
        tmp_cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{tmp_path}")
        command.upgrade(tmp_cfg, "head")
    finally:
        tmp_path.unlink(missing_ok=True)
