#!/bin/sh
set -euo pipefail

if [ "$#" -eq 0 ]; then
  set -- python -m tgcrm.bot.main
fi

python - <<'PYCODE'
import asyncio
import os

import asyncpg

from tgcrm.config import get_settings
from tgcrm.logging import configure_logging

configure_logging()

MAX_RETRIES = int(os.getenv("POSTGRES_WAIT_RETRIES", "60"))
SLEEP_SECONDS = float(os.getenv("POSTGRES_WAIT_DELAY", "1"))

async def wait_for_postgres() -> None:
    settings = get_settings()
    dsn = settings.database.async_dsn.replace("postgresql+asyncpg", "postgresql")
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            conn = await asyncpg.connect(dsn)
        except Exception as exc:  # pragma: no cover - transient connectivity
            print(f"[entrypoint] Waiting for PostgreSQL ({attempt}/{MAX_RETRIES}): {exc}", flush=True)
            await asyncio.sleep(SLEEP_SECONDS)
        else:
            await conn.close()
            print("[entrypoint] PostgreSQL is available.", flush=True)
            return
    raise RuntimeError("PostgreSQL did not become available in time")

asyncio.run(wait_for_postgres())
PYCODE

python -m tgcrm.db.manage init-db

echo "[entrypoint] Starting application: $*" >&2
exec "$@"
