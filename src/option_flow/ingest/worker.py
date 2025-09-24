from __future__ import annotations

import asyncio

from option_flow.services.rollups import RollupService

ROLLUP_INTERVAL_SECONDS = 5


async def rollup_loop() -> None:
    service = RollupService()
    while True:
        service.refresh_recent_minutes(60)
        await asyncio.sleep(ROLLUP_INTERVAL_SECONDS)


async def main() -> None:
    await rollup_loop()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
