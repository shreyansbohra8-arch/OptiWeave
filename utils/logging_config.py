"""Consistent logging setup."""
from __future__ import annotations

import logging

from config import settings

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_configured = False


def get_logger(name: str) -> logging.Logger:
    """Return a logger, configuring the root handler once."""
    global _configured
    if not _configured:
        logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL, logging.WARNING),
                            format=_FORMAT)
        _configured = True
    return logging.getLogger(name)
