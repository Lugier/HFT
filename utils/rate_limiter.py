"""
Rate limiter for API calls
"""
import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_second: float
    burst_size: int = 1


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for controlling API request rates
    """
    
    def __init__(self, rate: float, burst: int = 1):
        """
        Args:
            rate: Requests per second
            burst: Maximum burst size
        """
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait until a token is available"""
        wait_time = 0
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            # Add tokens based on elapsed time, but only if some time passed
            if elapsed > 0:
                self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
                self.last_update = now
            
            if self.tokens < 1:
                # Need to wait
                wait_time = (1 - self.tokens) / self.rate
                self.tokens = 0 # Reserve the token we're waiting for
            else:
                self.tokens -= 1
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)


class MultiRateLimiter:
    """
    Manages rate limiters for multiple sources (exchanges, chains)
    """
    
    def __init__(self):
        self._limiters: dict[str, TokenBucketRateLimiter] = {}
        self._lock = asyncio.Lock()
    
    def register(self, key: str, rate: float, burst: int = 1):
        """Register a rate limiter for a key"""
        self._limiters[key] = TokenBucketRateLimiter(rate, burst)
    
    async def acquire(self, key: str):
        """Acquire a token for the given key"""
        if key not in self._limiters:
            # Default rate limit if not registered
            async with self._lock:
                if key not in self._limiters:
                    self._limiters[key] = TokenBucketRateLimiter(10.0, 5)
        
        await self._limiters[key].acquire()


# Global rate limiter instance
rate_limiter = MultiRateLimiter()


def setup_rate_limiters():
    """Set up rate limiters for all configured sources"""
    from config.exchanges import EXCHANGES
    from config.chains import CHAINS
    
    # CEX rate limiters
    for exchange in EXCHANGES:
        rate_limiter.register(
            f"cex:{exchange.id}",
            exchange.rate_limit_per_second,
            burst=3
        )
    
    # Chain rate limiters (for RPC calls)
    for chain_id in CHAINS:
        # Conservative rate limit for free RPCs
        rate_limiter.register(
            f"chain:{chain_id.name}",
            25.0,  # 25 req/sec
            burst=5
        )
