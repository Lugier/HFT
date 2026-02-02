"""
Global settings for the Arbitrage Scanner
"""
from dataclasses import dataclass
from typing import Final

# Minimum profit threshold in USD (after gas fees)
MIN_PROFIT_USD: Final[float] = 5.0

# Trade size for profit calculations
DEFAULT_TRADE_SIZE_USD: Final[float] = 1000.0

# Maximum slippage tolerance (as decimal, 0.01 = 1%)
MAX_SLIPPAGE: Final[float] = 0.01

# Scan interval in seconds
SCAN_INTERVAL_SECONDS: Final[float] = 0.5

# Request timeout in seconds
REQUEST_TIMEOUT: Final[float] = 10.0

# Number of retries for failed requests
MAX_RETRIES: Final[int] = 3

# Logging level
LOG_LEVEL: Final[str] = "INFO"


@dataclass
class ProfitLevel:
    """Profit level thresholds for alerting"""
    threshold: float
    symbol: str
    name: str
    color: str


PROFIT_LEVELS: list[ProfitLevel] = [
    ProfitLevel(threshold=50.0, symbol="🚀", name="CRITICAL", color="red"),
    ProfitLevel(threshold=20.0, symbol="💰", name="HIGH", color="yellow"),
    ProfitLevel(threshold=5.0, symbol="💵", name="MEDIUM", color="green"),
]


def get_profit_level(profit_usd: float) -> ProfitLevel | None:
    """Get the profit level for a given profit amount"""
    for level in PROFIT_LEVELS:
        if profit_usd >= level.threshold:
            return level
    return None
