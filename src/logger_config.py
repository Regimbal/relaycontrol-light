"""Configure logging for the application."""

import logging
import sys

def setup_logging(level: str = "INFO") -> None:
    """Configure global logging with the given level."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True
    )
