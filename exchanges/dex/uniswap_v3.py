"""
Uniswap V3 style DEX implementation
Uses Quoter contract for price quotes
"""
from typing import Optional
from web3 import AsyncWeb3

from config.chains import ChainId, CHAINS
from config.tokens import ALL_TOKENS
from exchanges.dex.base_dex import BaseDEX, DEXPrice, UNISWAP_V3_QUOTER_ABI
from utils.rpc_manager import rpc_manager
from utils.rate_limiter import rate_limiter
from utils.logger import get_logger

logger = get_logger(__name__)


# Standard fee tiers for Uniswap V3
FEE_TIERS = [500, 3000, 10000]  # 0.05%, 0.3%, 1%


class UniswapV3DEX(BaseDEX):
    """
    Uniswap V3 style DEX implementation
    Uses the Quoter contract for accurate price quotes
    """
    
    def __init__(
        self,
        chain_id: ChainId,
        name: str,
        quoter_address: str,
    ):
        super().__init__(chain_id, name)
        self.quoter_address = quoter_address
        self._web3: Optional[AsyncWeb3] = None
        self._quoter_contract = None
    
    async def _get_web3(self) -> AsyncWeb3:
        """Get Web3 instance"""
        if self._web3 is None:
            self._web3 = await rpc_manager.get_web3(self.chain_id)
        return self._web3
    
    async def _get_quoter(self):
        """Get quoter contract"""
        if self._quoter_contract is None:
            web3 = await self._get_web3()
            self._quoter_contract = web3.eth.contract(
                address=web3.to_checksum_address(self.quoter_address),
                abi=UNISWAP_V3_QUOTER_ABI
            )
        return self._quoter_contract
    
    async def get_price(
        self,
        token_in: str,
        token_out: str,
        amount_in: int
    ) -> Optional[DEXPrice]:
        """Get price for a swap using the Quoter"""
        try:
            await rate_limiter.acquire(f"chain:{self.chain_id.name}")
            
            web3 = await self._get_web3()
            quoter = await self._get_quoter()
            
            # Checksum addresses
            token_in = web3.to_checksum_address(token_in)
            token_out = web3.to_checksum_address(token_out)
            
            best_amount_out = 0
            best_fee = 0
            
            # Try each fee tier and find the best quote
            for fee in FEE_TIERS:
                try:
                    # Use call to simulate the transaction
                    result = await quoter.functions.quoteExactInputSingle(
                        token_in,
                        token_out,
                        amount_in,
                        fee
                    ).call()
                    
                    amount_out = result[0]
                    if amount_out > best_amount_out:
                        best_amount_out = amount_out
                        best_fee = fee
                        
                except Exception:
                    continue
            
            if best_amount_out == 0:
                return None
            
            # Calculate price
            price = best_amount_out / amount_in
            fee_percent = best_fee / 10000  # Convert to percentage
            
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
                fee_percent=fee_percent
            )
            
        except Exception as e:
            logger.debug(f"Failed to get V3 price from {self.name}: {e}")
            return None
    
    async def get_reserves(
        self,
        token_a: str,
        token_b: str
    ) -> Optional[tuple[int, int]]:
        """
        V3 doesn't have simple reserves like V2
        Returns None as liquidity is tick-based
        """
        return None
    
    def _get_token_symbol(self, address: str) -> str:
        """Get token symbol from address"""
        address_lower = address.lower()
        for token in ALL_TOKENS:
            token_addr = token.get_address(self.chain_id)
            if token_addr and token_addr.lower() == address_lower:
                return token.symbol
        return address[:8] + "..."


def create_v3_instances() -> list[UniswapV3DEX]:
    """Create V3 DEX instances for all supported chains"""
    instances = []
    
    # Ethereum Uniswap V3
    eth_config = CHAINS[ChainId.ETHEREUM]
    if "uniswap_v3_quoter" in eth_config.dex_routers:
        instances.append(UniswapV3DEX(
            ChainId.ETHEREUM,
            "Uniswap V3",
            eth_config.dex_routers["uniswap_v3_quoter"]
        ))
    
    # BSC PancakeSwap V3
    bsc_config = CHAINS[ChainId.BSC]
    if "pancakeswap_v3_quoter" in bsc_config.dex_routers:
        instances.append(UniswapV3DEX(
            ChainId.BSC,
            "PancakeSwap V3",
            bsc_config.dex_routers["pancakeswap_v3_quoter"]
        ))
    
    # Polygon Uniswap V3
    polygon_config = CHAINS[ChainId.POLYGON]
    if "uniswap_v3_quoter" in polygon_config.dex_routers:
        instances.append(UniswapV3DEX(
            ChainId.POLYGON,
            "Uniswap V3 (Polygon)",
            polygon_config.dex_routers["uniswap_v3_quoter"]
        ))
    
    # Arbitrum Uniswap V3
    arb_config = CHAINS[ChainId.ARBITRUM]
    if "uniswap_v3_quoter" in arb_config.dex_routers:
        instances.append(UniswapV3DEX(
            ChainId.ARBITRUM,
            "Uniswap V3 (Arbitrum)",
            arb_config.dex_routers["uniswap_v3_quoter"]
        ))
    
    # Optimism Uniswap V3
    op_config = CHAINS[ChainId.OPTIMISM]
    if "uniswap_v3_quoter" in op_config.dex_routers:
        instances.append(UniswapV3DEX(
            ChainId.OPTIMISM,
            "Uniswap V3 (Optimism)",
            op_config.dex_routers["uniswap_v3_quoter"]
        ))
    
    # Base Uniswap V3
    base_config = CHAINS[ChainId.BASE]
    if "uniswap_v3_quoter" in base_config.dex_routers:
        instances.append(UniswapV3DEX(
            ChainId.BASE,
            "Uniswap V3 (Base)",
            base_config.dex_routers["uniswap_v3_quoter"]
        ))
    
    return instances
