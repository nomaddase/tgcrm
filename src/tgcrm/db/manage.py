"""Simple command-line utilities for database maintenance."""
from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Sequence

from tgcrm.db.session import init_models
from tgcrm.logging import configure_logging


def _configure_logging() -> None:
    configure_logging()
    logging.getLogger(__name__).debug("Logging configured for database management CLI.")


async def _handle_init_db() -> None:
    logger = logging.getLogger(__name__)
    logger.info("Ensuring database schema is up to date...")
    await init_models()
    logger.info("Database schema is up to date.")


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point for CLI commands."""

    parser = argparse.ArgumentParser(description="Database management utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db", help="Create database tables if they do not exist")

    args = parser.parse_args(argv)
    _configure_logging()

    if args.command == "init-db":
        asyncio.run(_handle_init_db())
    else:  # pragma: no cover - defensive programming
        raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
