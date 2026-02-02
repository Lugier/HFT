"""
Chain configurations with RPC endpoints
Expanded to include 10+ chains
"""
from dataclasses import dataclass, field
from typing import Final
from enum import Enum
import os
from dotenv import load_dotenv

load_dotenv()

INFURA_KEY = os.getenv("INFURA_API_KEY")



class ChainId(Enum):
    """Blockchain chain IDs"""
    ETHEREUM = 1
    BSC = 56
    POLYGON = 137
    ARBITRUM = 42161
    OPTIMISM = 10
    AVALANCHE = 43114
    FANTOM = 250
    BASE = 8453
    ZKSYNC = 324
    LINEA = 59144
    SCROLL = 534352
    GNOSIS = 100
    CRONOS = 25
    MOONBEAM = 1284
    CELO = 42220
    KAVA = 2222


@dataclass
class ChainConfig:
    """Configuration for a blockchain"""
    chain_id: ChainId
    name: str
    native_token: str
    native_decimals: int
    rpc_endpoints: list[str]
    explorer_url: str
    avg_block_time: float  # in seconds
    
    # DEX router addresses
    dex_routers: dict[str, str] = field(default_factory=dict)
    
    def get_rpc(self, index: int = 0) -> str:
        """Get RPC endpoint with rotation support, filtering None"""
        valid_rpcs = [r for r in self.rpc_endpoints if r is not None]
        return valid_rpcs[index % len(valid_rpcs)]


# Chain configurations with multiple free RPC endpoints for failover
CHAINS: dict[ChainId, ChainConfig] = {
    ChainId.ETHEREUM: ChainConfig(
        chain_id=ChainId.ETHEREUM,
        name="Ethereum",
        native_token="ETH",
        native_decimals=18,
        rpc_endpoints=[
            f"https://mainnet.infura.io/v3/{INFURA_KEY}" if INFURA_KEY else None,
            "https://eth.llamarpc.com",
            "https://rpc.ankr.com/eth",
            "https://ethereum.publicnode.com",
            "https://1rpc.io/eth",
            "https://cloudflare-eth.com",
            "https://eth.drpc.org",
        ],
        explorer_url="https://etherscan.io",
        avg_block_time=12.0,
        dex_routers={
            "uniswap_v2": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
            "uniswap_v3_quoter": "0x61fFE014bA17989E743c5F6cB21bF9697530B21e",
            "sushiswap": "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",
            "curve": "0x99a58482BD75cbab83b27EC03CA68fF489b5788f",
        }
    ),
    
    ChainId.BSC: ChainConfig(
        chain_id=ChainId.BSC,
        name="BSC",
        native_token="BNB",
        native_decimals=18,
        rpc_endpoints=[
            "https://bsc-dataseed.binance.org",
            "https://rpc.ankr.com/bsc",
            "https://bsc.publicnode.com",
            "https://bsc-dataseed1.defibit.io",
            "https://bsc-dataseed1.ninicoin.io",
            "https://bsc.drpc.org",
        ],
        explorer_url="https://bscscan.com",
        avg_block_time=3.0,
        dex_routers={
            "pancakeswap_v2": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
            "pancakeswap_v3_quoter": "0xB048Bbc1Ee6b733FFfCFb9e9CeF7375518e25997",
            "biswap": "0x3a6d8cA21D1CF76F653A67577FA0D27453350dD8",
        }
    ),
    
    ChainId.POLYGON: ChainConfig(
        chain_id=ChainId.POLYGON,
        name="Polygon",
        native_token="MATIC",
        native_decimals=18,
        rpc_endpoints=[
            f"https://polygon-mainnet.infura.io/v3/{INFURA_KEY}" if INFURA_KEY else None,
            "https://polygon-rpc.com",
            "https://rpc.ankr.com/polygon",
            "https://polygon.publicnode.com",
            "https://polygon-mainnet.public.blastapi.io",
            "https://polygon.drpc.org",
        ],
        explorer_url="https://polygonscan.com",
        avg_block_time=2.0,
        dex_routers={
            "quickswap": "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff",
            "sushiswap": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
            "uniswap_v3_quoter": "0x61fFE014bA17989E743c5F6cB21bF9697530B21e",
        }
    ),
    
    ChainId.ARBITRUM: ChainConfig(
        chain_id=ChainId.ARBITRUM,
        name="Arbitrum",
        native_token="ETH",
        native_decimals=18,
        rpc_endpoints=[
            f"https://arbitrum-mainnet.infura.io/v3/{INFURA_KEY}" if INFURA_KEY else None,
            "https://arb1.arbitrum.io/rpc",
            "https://rpc.ankr.com/arbitrum",
            "https://arbitrum.publicnode.com",
            "https://arbitrum-one.public.blastapi.io",
            "https://arbitrum.drpc.org",
        ],
        explorer_url="https://arbiscan.io",
        avg_block_time=0.25,
        dex_routers={
            "camelot": "0xc873fEcbd354f5A56E00E710B90EF4201db2448d",
            "sushiswap": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
            "uniswap_v3_quoter": "0x61fFE014bA17989E743c5F6cB21bF9697530B21e",
        }
    ),
    
    ChainId.OPTIMISM: ChainConfig(
        chain_id=ChainId.OPTIMISM,
        name="Optimism",
        native_token="ETH",
        native_decimals=18,
        rpc_endpoints=[
            f"https://optimism-mainnet.infura.io/v3/{INFURA_KEY}" if INFURA_KEY else None,
            "https://mainnet.optimism.io",
            "https://rpc.ankr.com/optimism",
            "https://optimism.publicnode.com",
            "https://optimism.drpc.org",
        ],
        explorer_url="https://optimistic.etherscan.io",
        avg_block_time=2.0,
        dex_routers={
            "velodrome": "0xa062aE8A9c5e11aaA026fc2670B0D65cCc8B2858",
            "uniswap_v3_quoter": "0x61fFE014bA17989E743c5F6cB21bF9697530B21e",
        }
    ),
    
    ChainId.AVALANCHE: ChainConfig(
        chain_id=ChainId.AVALANCHE,
        name="Avalanche",
        native_token="AVAX",
        native_decimals=18,
        rpc_endpoints=[
            f"https://avalanche-mainnet.infura.io/v3/{INFURA_KEY}" if INFURA_KEY else None,
            "https://api.avax.network/ext/bc/C/rpc",
            "https://rpc.ankr.com/avalanche",
            "https://avalanche.publicnode.com",
            "https://avalanche.drpc.org",
        ],
        explorer_url="https://snowtrace.io",
        avg_block_time=2.0,
        dex_routers={
            "traderjoe": "0x60aE616a2155Ee3d9A68541Ba4544862310933d4",
            "pangolin": "0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106",
        }
    ),
    
    ChainId.FANTOM: ChainConfig(
        chain_id=ChainId.FANTOM,
        name="Fantom",
        native_token="FTM",
        native_decimals=18,
        rpc_endpoints=[
            "https://rpc.ftm.tools",
            "https://rpc.ankr.com/fantom",
            "https://fantom.publicnode.com",
            "https://fantom.drpc.org",
        ],
        explorer_url="https://ftmscan.com",
        avg_block_time=1.0,
        dex_routers={
            "spookyswap": "0xF491e7B69E4244ad4002BC14e878a34207E38c29",
            "spiritswap": "0x16327E3FbDaCA3bcF7E38F5Af2599D2DDc33aE52",
        }
    ),
    
    ChainId.BASE: ChainConfig(
        chain_id=ChainId.BASE,
        name="Base",
        native_token="ETH",
        native_decimals=18,
        rpc_endpoints=[
            f"https://base-mainnet.infura.io/v3/{INFURA_KEY}" if INFURA_KEY else None,
            "https://mainnet.base.org",
            "https://rpc.ankr.com/base",
            "https://base.publicnode.com",
            "https://base.drpc.org",
        ],
        explorer_url="https://basescan.org",
        avg_block_time=2.0,
        dex_routers={
            "aerodrome": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
            "baseswap": "0x327Df1E6de05895d2ab08513aaDD9313Fe505d86",
            "uniswap_v3_quoter": "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a",
        }
    ),
    
    ChainId.ZKSYNC: ChainConfig(
        chain_id=ChainId.ZKSYNC,
        name="zkSync Era",
        native_token="ETH",
        native_decimals=18,
        rpc_endpoints=[
            "https://mainnet.era.zksync.io",
            "https://rpc.ankr.com/zksync_era",
            "https://zksync-era.drpc.org",
        ],
        explorer_url="https://explorer.zksync.io",
        avg_block_time=1.0,
        dex_routers={
            "syncswap": "0x2da10A1e27bF85cEdD8FFb1AbBe97e53391C0295",
            "mute": "0x8B791913eB07C32779a16750e3868aA8495F5964",
        }
    ),
    
    ChainId.LINEA: ChainConfig(
        chain_id=ChainId.LINEA,
        name="Linea",
        native_token="ETH",
        native_decimals=18,
        rpc_endpoints=[
            f"https://linea-mainnet.infura.io/v3/{INFURA_KEY}" if INFURA_KEY else None,
            "https://rpc.linea.build",
            "https://linea.drpc.org",
        ],
        explorer_url="https://lineascan.build",
        avg_block_time=2.0,
        dex_routers={
            "syncswap": "0x80e38291e06339d10AAB483C65695D004dBD5C69",
        }
    ),
    
    ChainId.SCROLL: ChainConfig(
        chain_id=ChainId.SCROLL,
        name="Scroll",
        native_token="ETH",
        native_decimals=18,
        rpc_endpoints=[
            "https://rpc.scroll.io",
            "https://scroll.drpc.org",
        ],
        explorer_url="https://scrollscan.com",
        avg_block_time=3.0,
        dex_routers={
            "syncswap": "0x80e38291e06339d10AAB483C65695D004dBD5C69",
        }
    ),
    
    ChainId.GNOSIS: ChainConfig(
        chain_id=ChainId.GNOSIS,
        name="Gnosis",
        native_token="xDAI",
        native_decimals=18,
        rpc_endpoints=[
            "https://rpc.gnosischain.com",
            "https://rpc.ankr.com/gnosis",
            "https://gnosis.drpc.org",
        ],
        explorer_url="https://gnosisscan.io",
        avg_block_time=5.0,
        dex_routers={
            "sushiswap": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
            "honeyswap": "0x1C232F01118CB8B424793ae03F870aa7D0ac7f77",
        }
    ),

    ChainId.CRONOS: ChainConfig(
        chain_id=ChainId.CRONOS,
        name="Cronos",
        native_token="CRO",
        native_decimals=18,
        rpc_endpoints=[
            "https://evm.cronos.org",
            "https://rpc.ankr.com/cronos",
            "https://cronos.drpc.org",
        ],
        explorer_url="https://cronoscan.com",
        avg_block_time=6.0,
        dex_routers={
            "vvs": "0x145863Eb42cf62847A6Ca784e6416C1682b1b2Ae",
            "mmf": "0x145677FC4d9b8F19B5D56d1820c48e0443049a30",
        }
    ),

    ChainId.MOONBEAM: ChainConfig(
        chain_id=ChainId.MOONBEAM,
        name="Moonbeam",
        native_token="GLMR",
        native_decimals=18,
        rpc_endpoints=[
            "https://rpc.api.moonbeam.network",
            "https://rpc.ankr.com/moonbeam",
            "https://moonbeam.publicnode.com",
        ],
        explorer_url="https://moonscan.io",
        avg_block_time=12.0,
        dex_routers={
            "stellaswap": "0xd3b39828414594c7C0C764A85375A2d574213702",
            "beamswap": "0x96b27695D71C1021bc789e5300B553259508BBD7",
        }
    ),

    ChainId.CELO: ChainConfig(
        chain_id=ChainId.CELO,
        name="Celo",
        native_token="CELO",
        native_decimals=18,
        rpc_endpoints=[
            f"https://celo-mainnet.infura.io/v3/{INFURA_KEY}" if INFURA_KEY else None,
            "https://forno.celo.org",
            "https://rpc.ankr.com/celo",
        ],
        explorer_url="https://celoscan.io",
        avg_block_time=5.0,
        dex_routers={
            "ubeswap": "0xE3D8bd6Aed4F159bc8000a9cD47CffDb95F96121",
        }
    ),

    ChainId.KAVA: ChainConfig(
        chain_id=ChainId.KAVA,
        name="Kava",
        native_token="KAVA",
        native_decimals=18,
        rpc_endpoints=[
            "https://evm.kava.io",
            "https://rpc.ankr.com/kava_evm",
        ],
        explorer_url="https://kavascan.com",
        avg_block_time=6.0,
        dex_routers={
            "equilibre": "0xA138FAFc30f6Ec6980aAd22656F2F11888151068",
        }
    ),
}


def get_chain(chain_id: ChainId) -> ChainConfig:
    """Get chain configuration by ID"""
    return CHAINS[chain_id]
