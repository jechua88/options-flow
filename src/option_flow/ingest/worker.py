from __future__ import annotations

import asyncio
import logging

from option_flow.config.settings import get_settings
from option_flow.ingest.live import LiveTradeService
from option_flow.services.rollups import RollupService

ROLLUP_INTERVAL_SECONDS = 5
LOGGER = logging.getLogger(__name__)


async def rollup_loop() -> None:
    service = RollupService()
    while True:
        service.refresh_recent_minutes(60)
        await asyncio.sleep(ROLLUP_INTERVAL_SECONDS)


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


async def main() -> None:
    configure_logging()
    settings = get_settings()
    tasks = [asyncio.create_task(rollup_loop(), name="rollup_loop")]
    if settings.demo_mode:
        LOGGER.info("Demo mode enabled; live ingest loop is disabled.")
    else:
        live_service = LiveTradeService()
        tasks.append(asyncio.create_task(live_service.run(), name="polygon_ingest"))
    await asyncio.gather(*tasks)


def run() -> None:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        LOGGER.info("Ingest worker interrupted; shutting down.")


if __name__ == "__main__":
    run()
