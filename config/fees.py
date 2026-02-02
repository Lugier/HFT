"""
Static withdrawal fee configuration
"""
from config.chains import ChainId

# Estimated withdrawal fees in USD
# Conservative estimates based on average network conditions
WITHDRAWAL_FEES_USD = {
    # Mainnet is expensive
    ChainId.ETHEREUM: 15.0,
    
    # L2s and cheap chains
    ChainId.BSC: 1.0,
    ChainId.POLYGON: 0.5,
    ChainId.ARBITRUM: 1.0,
    ChainId.OPTIMISM: 1.0,
    ChainId.AVALANCHE: 0.5,
    ChainId.FANTOM: 0.5,
    ChainId.BASE: 0.5,
    ChainId.ZKSYNC: 1.0,
    ChainId.LINEA: 1.0,
    ChainId.SCROLL: 1.0,
    ChainId.GNOSIS: 0.1,
    ChainId.CRONOS: 0.5,
    ChainId.MOONBEAM: 0.5,
    ChainId.CELO: 0.1,
    ChainId.KAVA: 0.2,
}

def get_withdrawal_fee(chain_id: ChainId | None) -> float:
    """Get estimated withdrawal fee for a chain"""
    if chain_id is None:
        # If no chain (e.g. CEX internal?), assume 0 or expensive?
        # Usually CEX -> CEX is crypto transfer, so usage is CEX -> DEX (Chain)
        return 0.0
    return WITHDRAWAL_FEES_USD.get(chain_id, 5.0)  # Default $5 safety
