"""
Uniswap V2 style DEX implementation
Works for: Uniswap V2, SushiSwap, PancakeSwap V2, QuickSwap, Camelot, and more
"""
from typing import Optional
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
        """Get pool reserves"""
        try:
            await rate_limiter.acquire(f"chain:{self.chain_id.name}")
            
            web3 = await self._get_web3()
            factory_address = await self._get_factory_address()
            
            # Get factory contract
            factory = web3.eth.contract(
                address=web3.to_checksum_address(factory_address),
                abi=UNISWAP_V2_FACTORY_ABI
            )
            
            # Get pair address
            token_a = web3.to_checksum_address(token_a)
            token_b = web3.to_checksum_address(token_b)
            pair_address = await factory.functions.getPair(token_a, token_b).call()
            
            if pair_address == "0x0000000000000000000000000000000000000000":
                return None
            
            # Get pair contract
            pair = web3.eth.contract(
                address=pair_address,
                abi=UNISWAP_V2_PAIR_ABI
            )
            
            # Get reserves
            reserves = await pair.functions.getReserves().call()
            token0 = await pair.functions.token0().call()
            
            # Order reserves correctly
            if token0.lower() == token_a.lower():
                return (reserves[0], reserves[1])
            else:
                return (reserves[1], reserves[0])
            
        except Exception as e:
            logger.debug(f"Failed to get reserves: {e}")
            return None
    
    def _get_token_symbol(self, address: str) -> str:
        """Get token symbol from address"""
        address_lower = address.lower()
        for token in ALL_TOKENS:
            token_addr = token.get_address(self.chain_id)
            if token_addr and token_addr.lower() == address_lower:
                return token.symbol
        return address[:8] + "..."


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
