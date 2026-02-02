#!/usr/bin/env python3
"""Quick test script for the arbitrage scanner"""
import asyncio
from exchanges.cex.ccxt_fetcher import cex_fetcher

async def test():
    print('🔄 Initializing CEX Fetcher...')
    await cex_fetcher.initialize()
    print('✅ CEX Fetcher initialized!')
    
    print('🔄 Fetching ETH/USDT prices from all exchanges...')
    prices = await cex_fetcher.fetch_all_prices([('ETH', 'USDT')])
    
    eth_prices = prices.get('ETH/USDT', [])
    print(f'✅ Got {len(eth_prices)} price quotes for ETH/USDT:')
    for p in eth_prices:
        print(f'   {p.exchange}: Bid=${p.bid:.2f}, Ask=${p.ask:.2f}, Spread={p.spread_pct:.3f}%')
    
    if len(eth_prices) >= 2:
        min_price = min(p.ask for p in eth_prices)
        max_price = max(p.bid for p in eth_prices)
        spread = ((max_price - min_price) / min_price) * 100
        print(f'\n📊 Max spread across exchanges: {spread:.3f}%')
        if spread > 0:
            print('   ✅ Arbitrage opportunity potentially exists!')
    
    await cex_fetcher.close()
    print('\n✅ Test complete!')

if __name__ == '__main__':
    asyncio.run(test())
