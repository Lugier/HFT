"""
Uniswap V2 style DEX implementation
Works for: Uniswap V2, SushiSwap, PancakeSwap V2, QuickSwap, Camelot, and more
"""
from typing import Optional, Any
from web3 import AsyncWeb3

from config.chains import ChainId, CHAINS
from config.tokens import Token, ALL_TOKENS
from exchanges.dex.base_dex import (
    BaseDEX, DEXPrice,
    UNISWAP_V2_ROUTER_ABI, UNISWAP_V2_PAIR_ABI, UNISWAP_V2_FACTORY_ABI
)
from utils.rpc_manager import rpc_manager
from utils.rate_limiter import rate_limiter
from utils.logger import get_logger
from core.network.multicall import Call

logger = get_logger(__name__)


class UniswapV2DEX(BaseDEX):
    """
    Uniswap V2 style DEX implementation
    Uses the getAmountsOut function for price quotes
    """
    
    def __init__(
        self,
        chain_id: ChainId,
        name: str,
        router_address: str,
        fee_percent: float = 0.3
    ):
        super().__init__(chain_id, name)
        self.router_address = router_address
        self.fee_percent = fee_percent
        self._factory_address: Optional[str] = None
        self._web3: Optional[AsyncWeb3] = None
        self._router_contract = None
        
        # Caches to reduce RPC calls
        self._pair_cache: dict[str, str] = {}  # "tokenA-tokenB" -> pair_address
        self._token0_cache: dict[str, str] = {}  # pair_address -> token0_address
    
    async def _get_web3(self) -> AsyncWeb3:
        """Get Web3 instance"""
        if self._web3 is None:
            self._web3 = await rpc_manager.get_web3(self.chain_id)
        return self._web3
    
    async def _get_router(self):
        """Get router contract"""
        if self._router_contract is None:
            web3 = await self._get_web3()
            self._router_contract = web3.eth.contract(
                address=web3.to_checksum_address(self.router_address),
                abi=UNISWAP_V2_ROUTER_ABI
            )
        return self._router_contract
    
    async def _get_factory_address(self) -> str:
        """Get factory address from router"""
        if self._factory_address is None:
            router = await self._get_router()
            self._factory_address = await router.functions.factory().call()
        return self._factory_address
    
    async def get_price(
        self,
        token_in: str,
        token_out: str,
        amount_in: int
    ) -> Optional[DEXPrice]:
        """Get price for a swap using getAmountsOut"""
        try:
            await rate_limiter.acquire(f"chain:{self.chain_id.name}")
            
            web3 = await self._get_web3()
            router = await self._get_router()
            
            # Checksum addresses
            token_in = web3.to_checksum_address(token_in)
            token_out = web3.to_checksum_address(token_out)
            
            # Get amounts out
            path = [token_in, token_out]
            amounts = await router.functions.getAmountsOut(amount_in, path).call()
            
            if len(amounts) < 2 or amounts[1] == 0:
                return None
            
            # Calculate price (amount_out / amount_in)
            price = amounts[1] / amount_in
            
            # Find token symbols
            token_in_symbol = self._get_token_symbol(token_in)
            token_out_symbol = self._get_token_symbol(token_out)
            
            return DEXPrice(
                dex_name=self.name,
                chain=self.chain_id,
                symbol=f"{token_in_symbol}/{token_out_symbol}",
                token_in=token_in,
                token_out=token_out,
                price=price,
                fee_percent=self.fee_percent
            )
            
        except Exception as e:
            logger.debug(f"Failed to get price from {self.name}: {e}")
            return None
    
    async def get_reserves(
        self,
        token_a: str,
        token_b: str
    ) -> Optional[tuple[int, int]]:
        """Get pool reserves with caching"""
        try:
            # Normalize addresses
            web3 = await self._get_web3()
            token_a = web3.to_checksum_address(token_a)
            token_b = web3.to_checksum_address(token_b)
            
            # 1. Check Pair Cache
            pair_key = f"{token_a}-{token_b}"
            pair_key_rev = f"{token_b}-{token_a}"
            
            if pair_key in self._pair_cache:
                pair_address = self._pair_cache[pair_key]
            elif pair_key_rev in self._pair_cache:
                pair_address = self._pair_cache[pair_key_rev]
            else:
                # Fetch from factory
                await rate_limiter.acquire(f"chain:{self.chain_id.name}")
                factory_address = await self._get_factory_address()
                factory = web3.eth.contract(
                    address=web3.to_checksum_address(factory_address),
                    abi=UNISWAP_V2_FACTORY_ABI
                )
                pair_address = await factory.functions.getPair(token_a, token_b).call()
                
                if pair_address == "0x0000000000000000000000000000000000000000":
                    return None
                
                # Cache it
                self._pair_cache[pair_key] = pair_address
            
            # Get pair contract
            pair = web3.eth.contract(
                address=pair_address,
                abi=UNISWAP_V2_PAIR_ABI
            )
            
            # 2. Get Reserves (Always fresh)
            await rate_limiter.acquire(f"chain:{self.chain_id.name}")
            reserves = await pair.functions.getReserves().call()
            
            # 3. Check Token0 Cache
            if pair_address in self._token0_cache:
                token0 = self._token0_cache[pair_address]
            else:
                token0 = await pair.functions.token0().call()
                self._token0_cache[pair_address] = token0
            
            # Order reserves correctly
            if token0.lower() == token_a.lower():
                return (reserves[0], reserves[1])
            else:
                return (reserves[1], reserves[0])
            
        except Exception as e:
            logger.debug(f"Failed to get reserves for {token_a}-{token_b} on {self.name}: {e}")
            return None
    
    def _get_token_symbol(self, address: str) -> str:
        """Get token symbol from address"""
        address_lower = address.lower()
        for token in ALL_TOKENS:
            token_addr = token.get_address(self.chain_id)
            if token_addr and token_addr.lower() == address_lower:
                return token.symbol
        return address[:8] + "..."

    def get_price_call_data(
        self,
        token_in: str,
        token_out: str,
        amount_in: int
    ) -> list[Call]:
        """Get call data for multicall"""
        try:
            # We need the Web3 instance to checksum addresses, but this method shouldn't be async
            # So we assume addresses are valid or handle normalization later?
            # Ideally we check correct format here.
            token_in = AsyncWeb3.to_checksum_address(token_in)
            token_out = AsyncWeb3.to_checksum_address(token_out)
            
            # Encode call data manually or use contract helper if available sync?
            # Web3.py contract functions usually require an instance.
            # We can construct the calldata manually using ABI encoding.
            # getAmountsOut(uint256 amountIn, address[] path)
            
            # Selector for getAmountsOut: 0xd06ca61f
            # But relying on web3 contract encodeABI is safer.
            
            # Since we can't easily get the contract instance synchronously without async init,
            # we'll do a lightweight encoding manually or accept that we need to init first.
            # BUT: This method is called by aggregator which manages init.
            
            if not self._router_contract:
                return [] # Interface restriction: must be governed by aggregator
                
            path = [token_in, token_out]
            call_data = self._router_contract.encodeABI(
                fn_name="getAmountsOut",
                args=[amount_in, path]
            )
            
            return [Call(
                target=self.router_address,
                allow_failure=True,
                call_data=bytes.fromhex(call_data[2:]), # remove 0x prefix
                output_types=['uint256[]']
            )]
        except Exception as e:
            logger.error(f"Failed to encode call data: {e}")
            return []

    def process_multicall_result(
        self,
        result: Any,
        token_in: str,
        token_out: str,
        amount_in: int,
        call_index: int = 0
    ) -> Optional[DEXPrice]:
        """Process V2 result (amounts array)"""
        try:
            # result is [amounts[]] due to tuple return type decoding
            # Actually, decode in multicall.py returns the decoded tuple.
            # output_types=['uint256[]'] -> result is ([amountIn, amountOut],)
            # wait, eth_abi.decode returns a tuple.
            # For ['uint256[]'], it returns ([123, 456],)
            
            if not result or len(result) == 0:
                return None
            
            # The result from Multicall3 wrapper is typically the inner value if single return
            # But let's be careful. My Multicall wrapper unwraps single values.
            # If output_types=['uint256[]'], result is [123, 456] (list of int)
            
            amounts = result
            if isinstance(result, tuple):
                 amounts = result[0]
            
            if not isinstance(amounts, list) or len(amounts) < 2:
                 return None

            amount_out = amounts[1]
            if amount_out == 0:
                return None
                
            price = amount_out / amount_in
            
            token_in_symbol = self._get_token_symbol(token_in)
            token_out_symbol = self._get_token_symbol(token_out)
            
            return DEXPrice(
                dex_name=self.name,
                chain=self.chain_id,
                symbol=f"{token_in_symbol}/{token_out_symbol}",
                token_in=token_in,
                token_out=token_out,
                price=price,
                fee_percent=self.fee_percent
            )
        except Exception:
            return None


def create_dex_instances() -> list[UniswapV2DEX]:
    """Create DEX instances for all supported chains"""
    instances = []
    
    # Ethereum DEXs
    eth_config = CHAINS[ChainId.ETHEREUM]
    if "uniswap_v2" in eth_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.ETHEREUM, "Uniswap V2", eth_config.dex_routers["uniswap_v2"], 0.3
        ))
    if "sushiswap" in eth_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.ETHEREUM, "SushiSwap (ETH)", eth_config.dex_routers["sushiswap"], 0.3
        ))
    
    # BSC DEXs
    bsc_config = CHAINS[ChainId.BSC]
    if "pancakeswap_v2" in bsc_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.BSC, "PancakeSwap V2", bsc_config.dex_routers["pancakeswap_v2"], 0.25
        ))
    if "biswap" in bsc_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.BSC, "BiSwap", bsc_config.dex_routers["biswap"], 0.1
        ))
    
    # Polygon DEXs
    polygon_config = CHAINS[ChainId.POLYGON]
    if "quickswap" in polygon_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.POLYGON, "QuickSwap", polygon_config.dex_routers["quickswap"], 0.3
        ))
    if "sushiswap" in polygon_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.POLYGON, "SushiSwap (Polygon)", polygon_config.dex_routers["sushiswap"], 0.3
        ))
    
    # Arbitrum DEXs
    arb_config = CHAINS[ChainId.ARBITRUM]
    if "camelot" in arb_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.ARBITRUM, "Camelot", arb_config.dex_routers["camelot"], 0.3
        ))
    if "sushiswap" in arb_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.ARBITRUM, "SushiSwap (Arbitrum)", arb_config.dex_routers["sushiswap"], 0.3
        ))
    
    # Optimism DEXs
    op_config = CHAINS[ChainId.OPTIMISM]
    if "velodrome" in op_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.OPTIMISM, "Velodrome", op_config.dex_routers["velodrome"], 0.02
        ))
    
    # Avalanche DEXs
    avax_config = CHAINS[ChainId.AVALANCHE]
    if "traderjoe" in avax_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.AVALANCHE, "TraderJoe", avax_config.dex_routers["traderjoe"], 0.3
        ))
    if "pangolin" in avax_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.AVALANCHE, "Pangolin", avax_config.dex_routers["pangolin"], 0.3
        ))
    
    # Fantom DEXs
    ftm_config = CHAINS[ChainId.FANTOM]
    if "spookyswap" in ftm_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.FANTOM, "SpookySwap", ftm_config.dex_routers["spookyswap"], 0.2
        ))
    if "spiritswap" in ftm_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.FANTOM, "SpiritSwap", ftm_config.dex_routers["spiritswap"], 0.3
        ))
    
    # Base DEXs
    base_config = CHAINS[ChainId.BASE]
    if "aerodrome" in base_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.BASE, "Aerodrome", base_config.dex_routers["aerodrome"], 0.02
        ))
    if "baseswap" in base_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.BASE, "BaseSwap", base_config.dex_routers["baseswap"], 0.25
        ))
    
    # zkSync DEXs
    zksync_config = CHAINS[ChainId.ZKSYNC]
    if "syncswap" in zksync_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.ZKSYNC, "SyncSwap (zkSync)", zksync_config.dex_routers["syncswap"], 0.3
        ))
    if "mute" in zksync_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.ZKSYNC, "Mute.io", zksync_config.dex_routers["mute"], 0.3
        ))
    
    # Linea DEXs
    linea_config = CHAINS[ChainId.LINEA]
    if "syncswap" in linea_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.LINEA, "SyncSwap (Linea)", linea_config.dex_routers["syncswap"], 0.3
        ))
    
    # Scroll DEXs
    scroll_config = CHAINS[ChainId.SCROLL]
    if "syncswap" in scroll_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.SCROLL, "SyncSwap (Scroll)", scroll_config.dex_routers["syncswap"], 0.3
        ))
    
    # Gnosis DEXs
    gnosis_config = CHAINS[ChainId.GNOSIS]
    if "sushiswap" in gnosis_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.GNOSIS, "SushiSwap (Gnosis)", gnosis_config.dex_routers["sushiswap"], 0.3
        ))
    if "honeyswap" in gnosis_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.GNOSIS, "Honeyswap", gnosis_config.dex_routers["honeyswap"], 0.3
        ))
    
    # Cronos DEXs
    cronos_config = CHAINS[ChainId.CRONOS]
    if "vvs" in cronos_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.CRONOS, "VVS Finance", cronos_config.dex_routers["vvs"], 0.3
        ))
    if "mmf" in cronos_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.CRONOS, "MM.Finance", cronos_config.dex_routers["mmf"], 0.17
        ))
        
    # Moonbeam DEXs
    moonbeam_config = CHAINS[ChainId.MOONBEAM]
    if "stellaswap" in moonbeam_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.MOONBEAM, "StellaSwap", moonbeam_config.dex_routers["stellaswap"], 0.25
        ))
    if "beamswap" in moonbeam_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.MOONBEAM, "BeamSwap", moonbeam_config.dex_routers["beamswap"], 0.3
        ))
    
    # Celo DEXs
    celo_config = CHAINS[ChainId.CELO]
    if "ubeswap" in celo_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.CELO, "Ubeswap", celo_config.dex_routers["ubeswap"], 0.3
        ))
    
    # Kava DEXs
    kava_config = CHAINS[ChainId.KAVA]
    if "equilibre" in kava_config.dex_routers:
        instances.append(UniswapV2DEX(
            ChainId.KAVA, "Equilibre", kava_config.dex_routers["equilibre"], 0.05
        ))
    
    return instances
