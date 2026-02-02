#!/usr/bin/env python3
"""
Crypto Arbitrage Scanner
========================
Multi-chain, multi-exchange arbitrage opportunity scanner

Monitors:
- 10+ CEXs (Binance, Coinbase, Kraken, etc.)
- 9 DEXs across 4 chains (ETH, BSC, Polygon, Arbitrum)

Usage:
    python main.py
"""
import asyncio
import signal
import sys

from utils.logger import setup_logging, get_logger
from utils.rate_limiter import setup_rate_limiters
from ui.terminal import dashboard

logger = get_logger(__name__)


async def main():
    """Main entry point"""
    # Setup
    setup_logging()
    setup_rate_limiters()
    
    logger.info("[bold blue]═══════════════════════════════════════════════════════════════[/bold blue]")
    logger.info("[bold cyan]          CRYPTO ARBITRAGE SCANNER v1.0                         [/bold cyan]")
    logger.info("[bold blue]═══════════════════════════════════════════════════════════════[/bold blue]")
    logger.info("")
    
    # Run dashboard
    try:
        await dashboard.run()
    except KeyboardInterrupt:
        logger.info("\n[yellow]Shutting down...[/yellow]")
    except Exception as e:
        logger.error(f"[red]Fatal error: {e}[/red]")
        raise
    finally:
        # Cleanup
        logger.info("[yellow]Cleaning up resources...[/yellow]")
        from exchanges.cex.ccxt_fetcher import cex_fetcher
        from exchanges.cex.ws_fetcher import ws_fetcher
        from utils.rpc_manager import rpc_manager
        
        # Stop background tasks first
        await ws_fetcher.stop()
        await cex_fetcher.close()
        await rpc_manager.close()
        logger.info("[green]Goodbye![/green]")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
