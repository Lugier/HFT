"""
Gas estimator for calculating transaction costs
"""
import asyncio
import sys
from dataclasses import dataclass
from typing import Optional

from config.chains import ChainId, CHAINS
from utils.rpc_manager import rpc_manager
from utils.rate_limiter import rate_limiter
from utils.logger import get_logger

logger = get_logger(__name__)


# Estimated gas usage for different operations
GAS_ESTIMATES = {
    "uniswap_v2_swap": 150_000,
    "uniswap_v3_swap": 180_000,
    "approval": 50_000,
    "transfer": 21_000,
}


@dataclass
class GasEstimate:
    """Gas cost estimate for a chain"""
    chain_id: ChainId
    chain_name: str
    gas_price_gwei: float
    native_token_price_usd: float
    swap_cost_usd: float
    v3_swap_cost_usd: float
    
    @property
    def total_arb_cost_usd(self) -> float:
        """Estimated cost for a full arbitrage (2 swaps)"""
        # Usually need 1 swap on each side
        return self.swap_cost_usd + self.v3_swap_cost_usd


class GasEstimator:
    """
    Estimates gas costs for transactions on different chains
    """
    
    def __init__(self):
        self._native_prices: dict[str, float] = {}
        self._last_update: float = 0
    
    async def _fetch_native_price(self, symbol: str) -> float:
        """Fetch native token price from the existing CEX fetcher"""
        try:
            from exchanges.cex.ccxt_fetcher import cex_fetcher
            
            # Try to get price from CEX fetcher
            price = await cex_fetcher.fetch_price("binance", symbol, "USDT")
            if price and price.mid > 0:
                return price.mid
            
            # Try OKX as fallback
            price = await cex_fetcher.fetch_price("okx", symbol, "USDC")
            if price and price.mid > 0:
                return price.mid
                
        except Exception:
            pass

        # Robust fallbacks for all supported chains
        fallbacks = {
            "ETH": 3000.0,
            "BNB": 500.0,
            "MATIC": 0.80,
            "AVAX": 40.0,
            "FTM": 0.50,
            "ARB": 1.20,
            "OP": 3.00,
            "SOL": 150.0,
            "CRO": 0.15,    # Cronos
            "GLMR": 0.40,   # Moonbeam
            "CELO": 0.80,   # Celo
            "KAVA": 0.70,   # Kava
            "xDAI": 1.0,    # Gnosis (stablecoin peg)
        }
        return fallbacks.get(symbol, 40.0)
    
    async def update_native_prices(self):
        """Update native token prices for all chains"""
        symbols = set()
        for chain in CHAINS.values():
            symbols.add(chain.native_token)
        
        tasks = [self._fetch_native_price(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for symbol, price in zip(symbols, results):
            if isinstance(price, (int, float)) and price > 0:
                self._native_prices[symbol] = price
                logger.debug(f"Native price {symbol}: ${price:.2f}")
    
    async def get_gas_estimate(self, chain_id: ChainId) -> Optional[GasEstimate]:
        """Get gas estimate for a chain"""
        try:
            # Get gas price
            await rate_limiter.acquire(f"chain:{chain_id.name}")
            gas_price_wei = await rpc_manager.get_gas_price(chain_id)
            gas_price_gwei = gas_price_wei / 1e9
            
            # Get native token price
            chain = CHAINS[chain_id]
            native_price = self._native_prices.get(chain.native_token, 0)
            
            if native_price == 0:
                await self.update_native_prices()
                native_price = self._native_prices.get(chain.native_token, 0)
            
            # Calculate costs
            v2_gas = GAS_ESTIMATES["uniswap_v2_swap"]
            v3_gas = GAS_ESTIMATES["uniswap_v3_swap"]
            
            v2_cost_eth = (v2_gas * gas_price_gwei) / 1e9
            v3_cost_eth = (v3_gas * gas_price_gwei) / 1e9
            
            v2_cost_usd = v2_cost_eth * native_price
            v3_cost_usd = v3_cost_eth * native_price
            
            # L2 Safety Multiplier for L1 Data Fees
            # Until we implement proper L1 fee estimation, we buffer the execution cost
            if chain_id in [ChainId.ARBITRUM, ChainId.OPTIMISM, ChainId.BASE, ChainId.LINEA, ChainId.SCROLL, ChainId.ZKSYNC]:
                v2_cost_usd *= 1.5
                v3_cost_usd *= 1.5
            
            return GasEstimate(
                chain_id=chain_id,
                chain_name=chain.name,
                gas_price_gwei=gas_price_gwei,
                native_token_price_usd=native_price,
                swap_cost_usd=v2_cost_usd,
                v3_swap_cost_usd=v3_cost_usd
            )
            
        except Exception as e:
            logger.debug(f"Failed to estimate gas for {chain_id.name}: {e}")
            return None
    
    async def get_all_gas_estimates(self) -> dict[ChainId, GasEstimate]:
        """Get gas estimates for all chains"""
        # First update native prices
        await self.update_native_prices()
        
        results = {}
        tasks = [(chain_id, self.get_gas_estimate(chain_id)) for chain_id in CHAINS.keys()]
        
        # Add a total timeout for gas estimation
        try:
            estimates = await asyncio.wait_for(
                asyncio.gather(*[t[1] for t in tasks], return_exceptions=True),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            print("  - Gas estimation timed out, using partial results.", flush=True)
            estimates = [None] * len(tasks)
        
        for (chain_id, _), estimate in zip(tasks, estimates):
            if isinstance(estimate, GasEstimate):
                results[chain_id] = estimate
        
        return results


# Global instance
gas_estimator = GasEstimator()
