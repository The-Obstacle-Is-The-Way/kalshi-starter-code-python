"""Logging configuration helpers (structlog)."""

from __future__ import annotations

import logging
import os
import sys

import structlog


def configure_structlog() -> None:
    """
    Configure structlog for this repository.

    Default behavior:
    - Logs go to stderr (keeps stdout clean for CLI output and `--json`).
    - Default level is WARNING (override with `KALSHI_LOG_LEVEL`).
    """
    level_name = os.getenv("KALSHI_LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.__stderr__),
        cache_logger_on_first_use=True,
    )
