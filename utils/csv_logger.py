import csv
import os
from datetime import datetime
from typing import Any
from pathlib import Path

class OpportunityLogger:
    """Logs arbitrage opportunities to a CSV file"""
    
    def __init__(self, filename: str = "arbitrage_opportunities.csv"):
        self.filename = filename
        self.headers = [
            "Timestamp",
            "Level",
            "Pair",
            "Buy Source",
            "Buy Price",
            "Sell Source",
            "Sell Price",
            "Spread %",
            "Gross Profit",
            "Gas Cost",
            "Fees",
            "Net Profit"
        ]
        self._ensure_file()
        
    def _ensure_file(self):
        """Create file with headers if it doesn't exist"""
        file_path = Path(self.filename)
        if not file_path.exists():
            with open(self.filename, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.headers)
    
    def log(self, opportunities: list[Any]):
        """Log a list of opportunities"""
        if not opportunities:
            return
            
        with open(self.filename, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for opp in opportunities:
                # Format timestamp
                ts = opp.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                
                # Format level
                level = opp.profit_level.name if opp.profit_level else "LOW"
                
                # Format sources
                buy_src = f"{opp.buy_source.source_name}"
                if opp.buy_source.chain:
                    buy_src += f" ({opp.buy_source.chain.name})"
                    
                sell_src = f"{opp.sell_source.source_name}"
                if opp.sell_source.chain:
                    sell_src += f" ({opp.sell_source.chain.name})"
                
                writer.writerow([
                    ts,
                    level,
                    opp.symbol,
                    buy_src,
                    f"{opp.buy_price:.6f}",
                    sell_src,
                    f"{opp.sell_price:.6f}",
                    f"{opp.spread_pct:.2f}%",
                    f"${opp.gross_profit_usd:.2f}",
                    f"${opp.gas_cost_usd:.2f}",
                    f"${opp.withdrawal_fee_usd:.2f}",
                    f"${opp.net_profit_usd:.2f}"
                ])
                
# Global instance
csv_logger = OpportunityLogger()
