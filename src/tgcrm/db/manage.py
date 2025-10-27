"""Simple command-line utilities for database maintenance."""
from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Sequence

from sqlalchemy.exc import OperationalError
from tenacity import AsyncRetrying, RetryError, retry_if_exception_type, stop_after_attempt, wait_exponential

from tgcrm.db.session import init_models
from tgcrm.logging import configure_logging


def _configure_logging() -> None:
    configure_logging()
    logging.getLogger(__name__).debug("Logging configured for database management CLI.")


async def _handle_init_db(max_attempts: int, backoff: float) -> None:
    logger = logging.getLogger(__name__)
    logger.info("Ensuring database schema is up to date...")

    retry_policy = AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=backoff, min=backoff, max=30),
        retry=retry_if_exception_type((ConnectionError, OperationalError, OSError)),
        reraise=True,
    )

    try:
        async for attempt in retry_policy:
            with attempt:
                logger.info(
                    "Attempt %s of %s to initialize database schema",
                    attempt.retry_state.attempt_number,
                    max_attempts,
                )
                await init_models()
    except RetryError as exc:  # pragma: no cover - defensive guard
        last_exc = exc.last_attempt.exception() if exc.last_attempt else exc
        logger.error("Failed to initialize database after %s attempts: %s", max_attempts, last_exc)
        raise SystemExit(1) from exc
    else:
        logger.info("Database schema is up to date.")


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point for CLI commands."""

    parser = argparse.ArgumentParser(description="Database management utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-db", help="Create database tables if they do not exist")
    init_parser.add_argument(
        "--max-attempts",
        type=int,
        default=5,
        help="Number of attempts to initialize the database before giving up (default: %(default)s)",
    )
    init_parser.add_argument(
        "--retry-backoff",
        type=float,
        default=1.0,
        help=(
            "Initial wait time between retry attempts in seconds. An exponential backoff is applied "
            "for subsequent retries (default: %(default)s)."
        ),
    )

    args = parser.parse_args(argv)
    _configure_logging()

    if args.command == "init-db":
        asyncio.run(_handle_init_db(args.max_attempts, args.retry_backoff))
    else:  # pragma: no cover - defensive programming
        raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
