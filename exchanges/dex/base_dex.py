"""
Base DEX class for all DEX implementations
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from config.chains import ChainId


@dataclass
class DEXPrice:
    """Price data from a DEX"""
    dex_name: str
    chain: ChainId
    symbol: str  # e.g., "ETH/USDT"
    token_in: str
    token_out: str
    price: float  # Price of 1 token_in in terms of token_out
    liquidity_usd: Optional[float] = None
    fee_percent: float = 0.3  # Default 0.3%
    
    @property
    def effective_price(self) -> float:
        """Price after DEX fees"""
        return self.price * (1 - self.fee_percent / 100)


class BaseDEX(ABC):
    """Abstract base class for DEX implementations"""
    
    def __init__(self, chain_id: ChainId, name: str):
        self.chain_id = chain_id
        self.name = name
    
    @abstractmethod
    async def get_price(
        self,
        token_in: str,
        token_out: str,
        amount_in: int
    ) -> Optional[DEXPrice]:
        """
        Get the price for swapping token_in to token_out
        
        Args:
            token_in: Address of input token
            token_out: Address of output token
            amount_in: Amount of input token (in wei/smallest unit)
        
        Returns:
            DEXPrice or None if pair doesn't exist or error
        """
        pass
    
    @abstractmethod
    async def get_reserves(
        self,
        token_a: str,
        token_b: str
    ) -> Optional[tuple[int, int]]:
        """
        Get pool reserves for a token pair
        
        Returns:
            Tuple of (reserve_a, reserve_b) or None if pool doesn't exist
        """
        pass


# Standard Uniswap V2 ABI for Router and Factory
UNISWAP_V2_ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"}
        ],
        "name": "getAmountsOut",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "factory",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "WETH",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

UNISWAP_V2_FACTORY_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"}
        ],
        "name": "getPair",
        "outputs": [{"internalType": "address", "name": "pair", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

UNISWAP_V2_PAIR_ABI = [
    {
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"internalType": "uint112", "name": "_reserve0", "type": "uint112"},
            {"internalType": "uint112", "name": "_reserve1", "type": "uint112"},
            {"internalType": "uint32", "name": "_blockTimestampLast", "type": "uint32"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token0",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Uniswap V3 Quoter ABI
UNISWAP_V3_QUOTER_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenIn", "type": "address"},
            {"internalType": "address", "name": "tokenOut", "type": "address"},
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint24", "name": "fee", "type": "uint24"}
        ],
        "name": "quoteExactInputSingle",
        "outputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
            {"internalType": "uint160", "name": "sqrtPriceX96After", "type": "uint160"},
            {"internalType": "uint32", "name": "initializedTicksCrossed", "type": "uint32"},
            {"internalType": "uint256", "name": "gasEstimate", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]
