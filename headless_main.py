
import asyncio
import logging
import time
from core.arbitrage_engine import arbitrage_engine
from utils.logger import setup_logging
from config.settings import DEFAULT_TRADE_SIZE_USD

# Setup verbose logging to file or stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting HEADLESS Arbitrage Scanner (Optimized)")
    
    # Init
    await arbitrage_engine.initialize()
    
    # Run a few scans
    for i in range(1, 4):
        logger.info(f"--- SCAN {i} ---")
        start = time.time()
        opps = await arbitrage_engine.scan()
        duration = time.time() - start
        
        logger.info(f"Scan {i} complete in {duration:.2f}s. Found {len(opps)} opportunities.")
        logger.info(f"Total pairs checked: {arbitrage_engine.total_pairs_checked}")
        
        # Check internal CEX fetcher state
        from exchanges.cex.ccxt_fetcher import cex_fetcher
        logger.info(f"CEX initialized exchanges: {len(cex_fetcher._exchanges)}")
        
        # Check DEX internal state (if possible)
        from exchanges.dex.aggregator import dex_aggregator
        # Peek at one V2 DEX cache if possible
        if dex_aggregator._v2_dexs:
            sample_dex = dex_aggregator._v2_dexs[0]
            if hasattr(sample_dex, '_pair_cache'):
                logger.info(f"Sample DEX Cache Size ({sample_dex.name}): {len(sample_dex._pair_cache)}")
        
        if len(opps) > 0:
            for j, opp in enumerate(opps[:5]):
                logger.info(f"OPP #{j+1}: {opp.symbol} | Spread: {opp.spread_pct:.2f}% | Profit: ${opp.net_profit_usd:.2f} | {opp.buy_source.source_id} -> {opp.sell_source.source_id}")
        
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
