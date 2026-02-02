"""
RPC Endpoint Manager with automatic failover and rotation
"""
import asyncio
import time
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable
from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.exceptions import Web3RPCError
import aiohttp
from config.chains import ChainId, ChainConfig, CHAINS

# Global optimized session for all network requests
_GLOBAL_SESSION: aiohttp.ClientSession | None = None

async def get_global_session() -> aiohttp.ClientSession:
    """Get or create a shared optimized session with advanced DNS caching"""
    global _GLOBAL_SESSION
    if _GLOBAL_SESSION is None or _GLOBAL_SESSION.closed:
        # ADVANCED DNS OPTIMIZATION:
        # Use a custom resolver with multiple high-speed DNS providers
        # This prevents the local OS/Router DNS bottleneck
        resolver = aiohttp.AsyncResolver(nameservers=["8.8.8.8", "1.1.1.1", "8.8.4.4"])
        
        connector = aiohttp.TCPConnector(
            use_dns_cache=True,
            ttl_dns_cache=600,     # Cache for 10 minutes
            limit=500,             # Increased connection limit for parallel scans
            limit_per_host=50,     # Higher limit per node
            enable_cleanup_closed=True,
            resolver=resolver      # Use custom async resolver
        )
        
        _GLOBAL_SESSION = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30, connect=10)
        )
    return _GLOBAL_SESSION


@dataclass
class RPCEndpointHealth:
    """Track health of an RPC endpoint"""
    url: str
    failures: int = 0
    last_failure: float = 0
    last_success: float = 0
    avg_latency_ms: float = 0
    
    def record_success(self, latency_ms: float):
        self.last_success = time.time()
        self.failures = 0
        # Exponential moving average
        if self.avg_latency_ms == 0:
            self.avg_latency_ms = latency_ms
        else:
            self.avg_latency_ms = 0.8 * self.avg_latency_ms + 0.2 * latency_ms
    
    def record_failure(self):
        self.failures += 1
        self.last_failure = time.time()
    
    def is_healthy(self) -> bool:
        # Consider unhealthy if 3+ failures in last 60 seconds
        if self.failures >= 3 and time.time() - self.last_failure < 60:
            return False
        return True


class RPCManager:
    """
    Manages RPC connections with failover and load balancing
    """
    
    def __init__(self):
        self._web3_instances: dict[ChainId, dict[str, AsyncWeb3]] = {}
        self._endpoint_health: dict[ChainId, dict[str, RPCEndpointHealth]] = {}
        self._current_index: dict[ChainId, int] = {}
        self._locks: dict[ChainId, asyncio.Lock] = {}
        
        # Initialize for all chains
        for chain_id, config in CHAINS.items():
            self._web3_instances[chain_id] = {}
            self._endpoint_health[chain_id] = {}
            self._current_index[chain_id] = 0
            self._locks[chain_id] = asyncio.Lock()
            
            for url in config.rpc_endpoints:
                self._endpoint_health[chain_id][url] = RPCEndpointHealth(url=url)
    
    async def _get_web3(self, chain_id: ChainId, url: str) -> AsyncWeb3:
        """Get or create a Web3 instance for a specific endpoint"""
        if url not in self._web3_instances[chain_id]:
            session = await get_global_session()
            provider = AsyncHTTPProvider(
                url,
                request_kwargs={"timeout": 15},
                # Note: Newer web3.py versions allow passing the session or use a global one
            )
            # Inject our shared session into the provider
            provider._request_session = session 
            self._web3_instances[chain_id][url] = AsyncWeb3(provider)
        return self._web3_instances[chain_id][url]
    
    def _get_best_endpoint(self, chain_id: ChainId) -> str:
        """Get the best available endpoint for a chain"""
        config = CHAINS[chain_id]
        healthy_endpoints = []
        
        for url in config.rpc_endpoints:
            health = self._endpoint_health[chain_id][url]
            if health.is_healthy():
                healthy_endpoints.append((url, health.avg_latency_ms or float('inf')))
        
        if not healthy_endpoints:
            # All unhealthy, reset and use first
            for url in config.rpc_endpoints:
                self._endpoint_health[chain_id][url].failures = 0
            return config.rpc_endpoints[0]
        
        # Sort by latency, return fastest
        healthy_endpoints.sort(key=lambda x: x[1])
        return healthy_endpoints[0][0]
    
    async def call(
        self,
        chain_id: ChainId,
        method: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute an RPC call with automatic failover
        """
        config = CHAINS[chain_id]
        last_error = None
        
        for attempt in range(len(config.rpc_endpoints)):
            url = self._get_best_endpoint(chain_id)
            web3 = await self._get_web3(chain_id, url)
            
            start_time = time.time()
            try:
                async def execute_call():
                    # Get the attribute from web3.eth
                    attr = getattr(web3.eth, method)
                    
                    # In Web3.py v6+, some are awaitable properties (gas_price, block_number)
                    if inspect.isawaitable(attr):
                        return await attr
                    elif callable(attr):
                        return await attr(*args, **kwargs)
                    else:
                        return attr

                result = await asyncio.wait_for(execute_call(), timeout=20.0)
                
                # Record success
                latency_ms = (time.time() - start_time) * 1000
                self._endpoint_health[chain_id][url].record_success(latency_ms)
                
                return result
                
            except Exception as e:
                self._endpoint_health[chain_id][url].record_failure()
                last_error = e
                continue
        
        raise Exception(f"All RPC endpoints failed for {config.name}: {last_error}")
    
    async def get_web3(self, chain_id: ChainId) -> AsyncWeb3:
        """Get a Web3 instance for the best available endpoint"""
        url = self._get_best_endpoint(chain_id)
        return await self._get_web3(chain_id, url)
    
    async def get_gas_price(self, chain_id: ChainId) -> int:
        """Get current gas price for a chain"""
        return await self.call(chain_id, "gas_price")
    
    async def get_block_number(self, chain_id: ChainId) -> int:
        """Get current block number for a chain"""
        return await self.call(chain_id, "block_number")

    async def close(self):
        """Close all Web3 providers"""
        for chain_id in self._web3_instances:
            for url in self._web3_instances[chain_id]:
                w3 = self._web3_instances[chain_id][url]
                try:
                    # AsyncWeb3 providers use disconnect()
                    if hasattr(w3.provider, "disconnect"):
                        await w3.provider.disconnect()
                except:
                    pass
        
        # Close global session
        global _GLOBAL_SESSION
        if _GLOBAL_SESSION and not _GLOBAL_SESSION.closed:
            await _GLOBAL_SESSION.close()
            _GLOBAL_SESSION = None


# Global RPC manager instance
rpc_manager = RPCManager()
