"""
CEX exchange configurations using CCXT
Expanded to include 25+ exchanges
"""
from dataclasses import dataclass
from typing import Final


@dataclass
class ExchangeConfig:
    """Configuration for a centralized exchange"""
    id: str  # CCXT exchange ID
    name: str
    rate_limit_per_second: float
    supports_public_api: bool = True


# Centralized exchanges to monitor (all support public API without keys)
EXCHANGES: list[ExchangeConfig] = [
    # Tier 1 - Major Exchanges
    ExchangeConfig(id="binance", name="Binance", rate_limit_per_second=20.0),
    ExchangeConfig(id="coinbase", name="Coinbase", rate_limit_per_second=10.0),
    ExchangeConfig(id="kraken", name="Kraken", rate_limit_per_second=1.0),
    ExchangeConfig(id="kucoin", name="KuCoin", rate_limit_per_second=10.0),
    ExchangeConfig(id="bybit", name="Bybit", rate_limit_per_second=2.0),
    ExchangeConfig(id="okx", name="OKX", rate_limit_per_second=10.0),
    ExchangeConfig(id="gateio", name="Gate.io", rate_limit_per_second=15.0),
    ExchangeConfig(id="htx", name="HTX (Huobi)", rate_limit_per_second=10.0),
    
    # Tier 2 - Large Exchanges
    ExchangeConfig(id="mexc", name="MEXC", rate_limit_per_second=20.0),
    ExchangeConfig(id="bitget", name="Bitget", rate_limit_per_second=20.0),
    ExchangeConfig(id="bitfinex", name="Bitfinex", rate_limit_per_second=1.5),
    ExchangeConfig(id="bitstamp", name="Bitstamp", rate_limit_per_second=1.0),
    ExchangeConfig(id="gemini", name="Gemini", rate_limit_per_second=1.0),
    ExchangeConfig(id="cryptocom", name="Crypto.com", rate_limit_per_second=5.0),
    ExchangeConfig(id="bingx", name="BingX", rate_limit_per_second=10.0),
    
    # Tier 3 - Medium Exchanges
    ExchangeConfig(id="bitmart", name="BitMart", rate_limit_per_second=5.0),
    ExchangeConfig(id="lbank", name="LBank", rate_limit_per_second=10.0),
    ExchangeConfig(id="phemex", name="Phemex", rate_limit_per_second=5.0),
    ExchangeConfig(id="whitebit", name="WhiteBit", rate_limit_per_second=10.0),
    ExchangeConfig(id="coinex", name="CoinEx", rate_limit_per_second=10.0),
    ExchangeConfig(id="exmo", name="EXMO", rate_limit_per_second=2.0),
    ExchangeConfig(id="poloniex", name="Poloniex", rate_limit_per_second=6.0),
    
    # Tier 4 - Smaller/Regional Exchanges
    ExchangeConfig(id="upbit", name="Upbit", rate_limit_per_second=5.0),
    ExchangeConfig(id="woo", name="WOO X", rate_limit_per_second=10.0),
    ExchangeConfig(id="ascendex", name="AscendEX", rate_limit_per_second=5.0),
    ExchangeConfig(id="digifinex", name="DigiFinex", rate_limit_per_second=5.0),
    ExchangeConfig(id="probit", name="ProBit", rate_limit_per_second=5.0),
    ExchangeConfig(id="xt", name="XT.com", rate_limit_per_second=10.0),
]


def get_exchange_by_id(exchange_id: str) -> ExchangeConfig | None:
    """Get exchange configuration by CCXT ID"""
    for exchange in EXCHANGES:
        if exchange.id == exchange_id:
            return exchange
    return None
