"""Command-line interface for database initialization.

This module allows running ``python -m tgcrm.db.init`` or importing the
:func:`main` function as an alias to the project-level database management
command. The implementation intentionally delegates to ``tgcrm.db.manage`` so
that the command-line surface stays consistent across different entrypoints
without duplicating argument parsing or retry logic.
"""
from __future__ import annotations

from typing import Sequence

from tgcrm.db.manage import main as _manage_main


def main(argv: Sequence[str] | None = None) -> None:
    """Execute the database initialization command.

    Parameters
    ----------
    argv:
        Additional command-line arguments to forward to the underlying
        management command. When ``None`` (the default), the command behaves as
        if ``["init-db"]`` was supplied, matching the behaviour of
        ``python -m tgcrm.db.init``.
    """

    args = ["init-db"]
    if argv:
        args.extend(argv)
    _manage_main(args)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
