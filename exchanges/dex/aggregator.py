"""
Combined DEX fetcher that aggregates prices from all DEXs
"""
import asyncio
import time
from dataclasses import dataclass
from typing import Optional

from config.chains import ChainId
from config.tokens import Token, ALL_TOKENS, get_tokens_for_chain, normalize_symbol
from config.settings import DEFAULT_TRADE_SIZE_USD
from exchanges.dex.base_dex import DEXPrice
from exchanges.dex.uniswap_v2 import UniswapV2DEX, create_dex_instances
from exchanges.dex.uniswap_v3 import UniswapV3DEX, create_v3_instances
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DEXQuote:
    """Aggregated DEX quote with normalized price"""
    dex_name: str
    chain: ChainId
    chain_name: str
    base_symbol: str
    quote_symbol: str
    bid: float  # Price to sell 1 base token (in quote tokens)
    ask: float  # Price to buy 1 base token (in quote tokens)
    fee_percent: float
    timestamp: float = 0

    
    @property
    def source_id(self) -> str:
        """Unique identifier for this price source"""
        return f"{self.dex_name}@{self.chain_name}"
    
    @property
    def normalized_symbol(self) -> str:
        """Normalized trading pair symbol"""
        return f"{normalize_symbol(self.base_symbol)}/{normalize_symbol(self.quote_symbol)}"


class DEXAggregator:
    """
    Aggregates prices from all DEXs across all chains
    """
    
    def __init__(self):
        self._v2_dexs: list[UniswapV2DEX] = []
        self._v3_dexs: list[UniswapV3DEX] = []
        self._initialized = False
        self._semaphore = asyncio.Semaphore(25)  # Lower concurrency to prevent RPC timeouts
    
    async def initialize(self):
        """Initialize all DEX instances"""
        if self._initialized:
            return
        
        self._v2_dexs = create_dex_instances()
        self._v3_dexs = create_v3_instances()
        
        logger.info(f"[bold green]DEX Aggregator ready: {len(self._v2_dexs)} V2 DEXs, {len(self._v3_dexs)} V3 DEXs[/bold green]")
        self._initialized = True
    
    def _get_token_pair_for_chain(
        self,
        chain_id: ChainId,
        base_symbol: str,
        quote_symbol: str
    ) -> Optional[tuple[Token, Token]]:
        """Get token pair addresses for a chain"""
        base_token = None
        quote_token = None
        
        for token in ALL_TOKENS:
            if token.symbol == base_symbol and chain_id in token.addresses:
                base_token = token
            if token.symbol == quote_symbol and chain_id in token.addresses:
                quote_token = token
        
        if base_token and quote_token:
            return (base_token, quote_token)
        return None
    
    async def get_price(
        self,
        base_symbol: str,
        quote_symbol: str,
        chain_id: ChainId,
        dex: UniswapV2DEX | UniswapV3DEX,
        amount: int = 10**18  # Default 1 token
    ) -> Optional[DEXQuote]:
        """Get price from a specific DEX"""
        tokens = self._get_token_pair_for_chain(chain_id, base_symbol, quote_symbol)
        if not tokens:
            return None
        
        base_token, quote_token = tokens
        base_address = base_token.get_address(chain_id)
        quote_address = quote_token.get_address(chain_id)
        
        if not base_address or not quote_address:
            return None
        
        # Get reserves and spot price
        # HFT Optimization: Use a larger semaphore and timeout
        try:
            async with self._semaphore:
                reserves_task = dex.get_reserves(base_address, quote_address)
                
                # Fetch price for a smaller amount checks
                # Smart Sizing: Use ~DEFAULT_TRADE_SIZE_USD worth of tokens
                target_amount_token = DEFAULT_TRADE_SIZE_USD / base_token.approx_price_usd
                # Clamp to minimum 1 unit to avoid 0
                if target_amount_token < 1e-6:
                     target_amount_token = 1e-6 # Minimum sane amount
                
                amount_in_spot = int(target_amount_token * (10 ** base_token.get_decimals(chain_id)))
                if amount_in_spot == 0:
                     amount_in_spot = 10 ** base_token.get_decimals(chain_id) # Fallback to 1 unit
                     
                spot_task = dex.get_price(base_address, quote_address, amount_in_spot)
                
                # 15s timeout for DEX calls - give public RPCs time
                reserves, spot_price_data = await asyncio.wait_for(
                    asyncio.gather(reserves_task, spot_task, return_exceptions=True),
                    timeout=15.0
                )
        except (asyncio.TimeoutError, Exception):
            return None
        
        # Validation
        if isinstance(spot_price_data, Exception) or not spot_price_data or spot_price_data.price <= 0:
            return None

        # LIQUIDITY CHECK (Crucial for HFT)
        # Filter out pools with low liquidity which cause massive slippage/price distortion
        if not isinstance(reserves, Exception) and reserves:
            res_in, res_out = reserves
            
            # 1. Check Raw Token Amounts (Avoid dust pools)
            # If base token reserves are too low (e.g. < 0.1 ETH), skip
            # Need approximate USD value. 
            
            # Calculate Spot Price from Reserves (Ratio) if possible (V2)
            # This is more accurate than getAmountsOut(1 Unit) for illiquid pools
            if res_in > 0:
                base_decimals = base_token.get_decimals(chain_id)
                quote_decimals = quote_token.get_decimals(chain_id)
                reserve_price = (res_out / (10**quote_decimals)) / (res_in / (10**base_decimals))
            else:
                reserve_price = 0
                
            # Use reserve price if reasonable, otherwise fallback to spot_price_data
            # But spot_price_data uses getAmountsOut(1 Unit) which distorts illiquid pools.
            # So Reserve Price is strictly better for V2.
            
            dec_adj = 10 ** (base_token.get_decimals(chain_id) - quote_token.get_decimals(chain_id))
            spot_price_from_quote = spot_price_data.price * dec_adj
            
            # Use the reserve price for V2 calculations if available
            spot_price = reserve_price if reserve_price > 0 else spot_price_from_quote
            
            # 2. Check Liquidity Value
            # Approx value in Quote Token (USD usually)
            liquidity_val = (res_out / (10**quote_token.get_decimals(chain_id)))
            
            # If quote is USDT/USDC/DAI (Stable), liquidity_val is approx USD.
            # If quote is ETH, we need ETH price.
            # Simple heuristic: Reject if < 1000 units of quote token (unless it's WBTC/ETH)
            # Better: $10k threshold.
            # Assuming most quotes are stables or ETH.
            threshold = 10000 
            if quote_symbol in ["ETH", "WETH", "BTC", "WBTC", "BNB", "WBNB"]:
                 threshold = 2 # Approx $4-5k for ETH, 
            
            if liquidity_val < threshold and quote_symbol not in ["ETH", "WETH", "BTC", "WBTC", "BNB", "WBNB"]:
                 # Strict check for stables
                 return None
            elif liquidity_val < 2 and quote_symbol in ["ETH", "WETH", "BTC", "WBTC", "BNB", "WBNB"]:
                 # Strict check for native
                 return None

            # Calculate actual slippage
            if spot_price > 0:
                trade_size_base = 1000.0 / spot_price
                trade_size_wei = int(trade_size_base * (10 ** base_token.get_decimals(chain_id)))
                
                # Sell impact
                sell_impact = trade_size_wei / (res_in + trade_size_wei)
                
                bid_price = spot_price * (1 - sell_impact)
                ask_price = spot_price * (1 + sell_impact)
            else:
                return None
        else:
            # Fallback for V3 (no reserves) or errors
            # V3 usually doesn't have the "1 ETH Swap distortion" as badly due to CL,
            # but we should still be careful.
            if isinstance(reserves, Exception) or not reserves:
                # If we lack reserve data (V3), use the quoted price but maybe add a penalty
                 dec_adj = 10 ** (base_token.get_decimals(chain_id) - quote_token.get_decimals(chain_id))
                 spot_price = spot_price_data.price * dec_adj
                 bid_price = spot_price
                 ask_price = spot_price
                 
                 # V3 Quoter handles impact in the quote? 
                 # get_price calls quoteExactInputSingle.
                 # If we requested 1 ETH, it returns output for 1 ETH.
                 # So price includes impact of 1 ETH.
                 # HACK: If returned price is significantly different from expected, it's illiquid.
                 pass

        # Final sanity check
        if bid_price <= 0 or ask_price <= 0 or bid_price > 1e12:
            return None
            
        return DEXQuote(
            dex_name=dex.name,
            chain=chain_id,
            chain_name=chain_id.name,
            base_symbol=base_symbol,
            quote_symbol=quote_symbol,
            bid=bid_price,
            ask=ask_price,
            fee_percent=dex.fee_percent,
            timestamp=time.time()
        )
    
    async def fetch_all_prices(
        self,
        pairs: list[tuple[str, str]]
    ) -> dict[str, list[DEXQuote]]:
        """
        Fetch prices for all pairs from all DEXs
        Returns dict: normalized_symbol -> list of quotes
        """
        if not self._initialized:
            await self.initialize()
        
        results: dict[str, list[DEXQuote]] = {}
        tasks = []
        task_info = []
        
        all_dexs = self._v2_dexs + self._v3_dexs
        
        for base, quote in pairs:
            normalized = f"{normalize_symbol(base)}/{normalize_symbol(quote)}"
            if normalized not in results:
                results[normalized] = []
            
            for dex in all_dexs:
                tasks.append(self.get_price(base, quote, dex.chain_id, dex))
                task_info.append(normalized)
        
        # Execute all fetches concurrently
        quotes = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Organize results
        for i, quote in enumerate(quotes):
            if isinstance(quote, DEXQuote):
                results[task_info[i]].append(quote)
        
        return results
    
    def get_all_dexs(self) -> list[str]:
        """Get list of all DEX names"""
        return [dex.name for dex in self._v2_dexs + self._v3_dexs]


# Global instance
dex_aggregator = DEXAggregator()
