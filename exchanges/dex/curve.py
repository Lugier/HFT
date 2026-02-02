"""
Curve Finance DEX Implementation
Uses the Curve Router to find best rates across pools.
"""
from typing import Optional, Any
from web3 import AsyncWeb3

from config.chains import ChainId, CHAINS
from exchanges.dex.base_dex import BaseDEX, DEXPrice
from utils.rpc_manager import rpc_manager
from utils.rate_limiter import rate_limiter
from utils.logger import get_logger
from core.network.multicall import Call

logger = get_logger(__name__)

# Curve Router v1 ABI
# function get_best_rate(address _from, address _to, uint256 _amount) view returns (address, uint256)
CURVE_ROUTER_ABI = [
    {
        "name": "get_best_rate",
        "inputs": [
            {"name": "_from", "type": "address"},
            {"name": "_to", "type": "address"},
            {"name": "_amount", "type": "uint256"}
        ],
        "outputs": [
            {"name": "", "type": "address"}, # Pool address
            {"name": "", "type": "uint256"} # Amount out
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

class CurveDEX(BaseDEX):
    """
    Curve Finance Adapter using Router
    """
    def __init__(self, chain_id: ChainId, router_address: str):
        super().__init__(chain_id, "Curve")
        self.router_address = router_address
        self._web3: Optional[AsyncWeb3] = None
        self._router_contract = None
        self.fee_percent = 0.0004 # Approx 0.04% base fee, varies by pool

    async def _get_web3(self) -> AsyncWeb3:
        if self._web3 is None:
            self._web3 = await rpc_manager.get_web3(self.chain_id)
        return self._web3

    async def _get_router(self):
        if self._router_contract is None:
            web3 = await self._get_web3()
            self._router_contract = web3.eth.contract(
                address=web3.to_checksum_address(self.router_address),
                abi=CURVE_ROUTER_ABI
            )
        return self._router_contract

    async def get_price(
        self,
        token_in: str,
        token_out: str,
        amount_in: int
    ) -> Optional[DEXPrice]:
        try:
            await rate_limiter.acquire(f"chain:{self.chain_id.name}")
            router = await self._get_router()
            web3 = await self._get_web3()
            
            t_in = web3.to_checksum_address(token_in)
            t_out = web3.to_checksum_address(token_out)
            
            # call get_best_rate
            result = await router.functions.get_best_rate(t_in, t_out, amount_in).call()
            # result is (pool_address, amount_out)
            
            pool_addr, amount_out = result
            
            if amount_out == 0 or pool_addr == "0x0000000000000000000000000000000000000000":
                return None
                
            price = amount_out / amount_in
            
            return DEXPrice(
                dex_name=self.name,
                chain=self.chain_id,
                symbol=f"{token_in}/{token_out}", # Raw addresses for now, aggregator resolves symbols
                token_in=token_in,
                token_out=token_out,
                price=price,
                fee_percent=self.fee_percent
            )
            
        except Exception as e:
            # logger.debug(f"Curve get_price failed: {e}")
            return None

    async def get_reserves(self, token_a: str, token_b: str) -> Optional[tuple[int, int]]:
        # Curve is complex, reserves are per pool.
        # Router doesn't expose easy reserves.
        # Return None to rely on quoted price (it's stable swap anyway).
        return None

    def get_price_call_data(
        self,
        token_in: str,
        token_out: str,
        amount_in: int
    ) -> list[Call]:
        try:
            if not self._router_contract:
                 return []
                 
            t_in = AsyncWeb3.to_checksum_address(token_in)
            t_out = AsyncWeb3.to_checksum_address(token_out)
            
            call_data = self._router_contract.encodeABI(
                fn_name="get_best_rate",
                args=[t_in, t_out, amount_in]
            )
            
            return [Call(
                target=self.router_address,
                allow_failure=True,
                call_data=bytes.fromhex(call_data[2:]),
                output_types=['address', 'uint256']
            )]
        except Exception:
            return []

    def process_multicall_result(
        self,
        result: Any,
        token_in: str,
        token_out: str,
        amount_in: int,
        call_index: int = 0
    ) -> Optional[DEXPrice]:
        try:
            if not result:
                return None
            
            # Output: (pool_address, amount_out)
            # Wrapper returns list/tuple
            
            data = result
            if isinstance(result, list) and len(result) == 1 and isinstance(result[0], tuple):
                 data = result[0] # Handle nested tuple if any? 
                 # Wait, decode returns (address, uint256) tuple inside the list?
                 # Multicall wrapper:
                 # if len(decoded) == 1: returns decoded[0]
                 # else: returns decoded (tuple)
                 
            # Here we have 2 outputs. So it returns (addr, uint).
            if not isinstance(data, (list, tuple)) or len(data) < 2:
                return None
                
            pool_addr = data[0]
            amount_out = data[1]
            
            if amount_out == 0:
                return None
                
            price = amount_out / amount_in
            
            return DEXPrice(
                dex_name=self.name,
                chain=self.chain_id,
                symbol=f"CURVE_PAIR", # Aggregator fixes this
                token_in=token_in,
                token_out=token_out,
                price=price,
                fee_percent=self.fee_percent
            )
        except Exception:
            return None

def create_curve_instances() -> list[CurveDEX]:
    instances = []
    # Add for chains that have Curve Router in config
    for chain_id, config in CHAINS.items():
        if "curve" in config.dex_routers:
            instances.append(CurveDEX(
                chain_id,
                config.dex_routers["curve"]
            ))
    return instances
