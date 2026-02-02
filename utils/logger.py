"""
Logging utilities
"""
import logging
import sys
from rich.logging import RichHandler
from rich.console import Console

from config.settings import LOG_LEVEL

# Global console for rich output
console = Console()


def setup_logging():
    """Configure logging with rich handler"""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                show_path=False,
                markup=True
            )
        ]
    )
    
    # Reduce noise from external libraries
    logging.getLogger("web3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("ccxt").setLevel(logging.WARNING)
    logging.getLogger("ccxt.base.exchange").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)
