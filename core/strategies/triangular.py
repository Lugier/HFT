"""
Triangular Arbitrage Strategy
Detects loops like A -> B -> C -> A on a single exchange.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict
from exchanges.cex.ccxt_fetcher import CEXPrice
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class TriangularOpportunity:
    exchange: str
    symbol_path: list[str] # ["BTC/USDT", "ETH/BTC", "ETH/USDT"]
    trade_path: list[str] # ["BUY", "BUY", "SELL"]
    expected_profit_pct: float
    timestamp: datetime = datetime.now()

class TriangularStrategy:
    """
    Finds triangular arbitrage opportunities on single exchanges
    """
    def __init__(self):
        self.min_profit_pct = 0.1 # 0.1% minimum
        
    def find_opportunities(self, cex_prices: dict[str, list[CEXPrice]]) -> list[TriangularOpportunity]:
        """
        Calculates all possible triangular loops for each exchange
        cex_prices: dict { symbol -> [CEXPrice, ...] }
        """
        # 1. Group prices by exchange
        prices_by_exchange: dict[str, dict[str, CEXPrice]] = {}
        for symbol, prices in cex_prices.items():
            for price in prices:
                if price.exchange not in prices_by_exchange:
                    prices_by_exchange[price.exchange] = {}
                prices_by_exchange[price.exchange][symbol] = price
                
        results = []
        
        # Hubs for efficient searching
        HUBS = ["USDT", "USDC", "BTC", "ETH"]
        
        for exchange, markets in prices_by_exchange.items():
            # Find possible triangles
            # We look for: BASE/HUB1, HUB1/HUB2, BASE/HUB2
            
            # Extract all bases
            symbols = list(markets.keys())
            bases = set()
            for s in symbols:
                if '/' in s:
                    bases.add(s.split('/')[0])
            
            for base in bases:
                if base in HUBS: continue
                
                for i in range(len(HUBS)):
                    for j in range(i + 1, len(HUBS)):
                        h1 = HUBS[i]
                        h2 = HUBS[j]
                        
                        # Possible Triple: (base/h1, h1/h2, base/h2)
                        p1_sym = f"{base}/{h1}"
                        p2_sym = f"{h1}/{h2}"
                        p3_sym = f"{base}/{h2}"
                        
                        if p1_sym in markets and p2_sym in markets and p3_sym in markets:
                            # Path: base -> h1 -> h2 -> base
                            # Trade 1: base -> h1 (SELL base/h1) -> amount_h1 = 1 * bid(base/h1)
                            # Trade 2: h1 -> h2 (BUY h1/h2) -> amount_h2 = amount_h1 / ask(h1/h2)
                            # Trade 3: h2 -> base (BUY base/h2) -> amount_base = amount_h2 / ask(base/h2)
                            
                            m1 = markets[p1_sym]
                            m2 = markets[p2_sym]
                            m3 = markets[p3_sym]
                            
                            # Forward: base -> h1 -> h2 -> base
                            try:
                                # Start with 1 unit of BASE
                                res1 = m1.bid # SELL base for h1
                                res2 = res1 / m2.ask # BUY h2 with h1
                                res3 = res2 / m3.ask # BUY base with h2
                                
                                profit = (res3 - 1.0) * 100
                                if profit > self.min_profit_pct:
                                    results.append(TriangularOpportunity(
                                        exchange=exchange,
                                        symbol_path=[p1_sym, p2_sym, p3_sym],
                                        trade_path=["SELL", "BUY", "BUY"],
                                        expected_profit_pct=profit
                                    ))
                                    
                                # Reverse: base -> h2 -> h1 -> base
                                # Trade 1: base -> h2 (SELL base/h2) -> amount_h2 = 1 * bid(base/h2)
                                # Trade 2: h2 -> h1 (SELL h1/h2 is h2 for h1) -> amount_h1 = amount_h2 * bid(h1/h2)
                                # Trade 3: h1 -> base (BUY base/h1) -> amount_base = amount_h1 / ask(base/h1)
                                
                                r_res1 = m3.bid
                                r_res2 = r_res1 * m2.bid
                                r_res3 = r_res2 / m1.ask
                                
                                r_profit = (r_res3 - 1.0) * 100
                                if r_profit > self.min_profit_pct:
                                    results.append(TriangularOpportunity(
                                        exchange=exchange,
                                        symbol_path=[p3_sym, p2_sym, p1_sym],
                                        trade_path=["SELL", "SELL", "BUY"],
                                        expected_profit_pct=r_profit
                                    ))
                            except:
                                continue
                                
        return results

triangular_strategy = TriangularStrategy()
