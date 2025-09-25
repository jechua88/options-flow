from __future__ import annotations

import logging
from typing import Mapping, Sequence

DEFAULT_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(level: str = "INFO", *, extra_handlers: Sequence[logging.Handler] | None = None) -> None:
    """Configure root logging with a consistent format.

    Additional handlers (file, streaming, etc.) can be supplied via ``extra_handlers``.
    """

    logging.basicConfig(level=level.upper(), format=DEFAULT_FORMAT)
    if extra_handlers:
        root = logging.getLogger()
        for handler in extra_handlers:
            root.addHandler(handler)


__all__ = ["configure_logging"]
