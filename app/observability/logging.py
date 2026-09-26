"""Structured key-value request logging without question or answer text."""

import logging


def configure_logging(level):
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return logging.getLogger("medical_rag")
