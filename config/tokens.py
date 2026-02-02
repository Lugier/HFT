"""
Token configurations per chain
Expanded to 50+ tokens with addresses across all chains
"""
from dataclasses import dataclass, field
from config.chains import ChainId


@dataclass
class Token:
    """Token configuration"""
    symbol: str
    name: str
    decimals: int
    addresses: dict[ChainId, str]  # Chain ID -> Contract address
    chain_decimals: dict[ChainId, int] = field(default_factory=dict)  # Overrides per chain
    approx_price_usd: float = 1.0  # Approximate price for trade sizing
    
    def get_address(self, chain_id: ChainId) -> str | None:
        """Get token address for a specific chain"""
        return self.addresses.get(chain_id)

    def get_decimals(self, chain_id: ChainId) -> int:
        """Get token decimals for a specific chain"""
        return self.chain_decimals.get(chain_id, self.decimals)


# ==================== STABLECOINS ====================

USDT = Token(
    symbol="USDT",
    name="Tether USD",
    decimals=6,
    addresses={
        ChainId.ETHEREUM: "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        ChainId.BSC: "0x55d398326f99059fF775485246999027B3197955",
        ChainId.POLYGON: "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
        ChainId.ARBITRUM: "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        ChainId.OPTIMISM: "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
        ChainId.AVALANCHE: "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",
        ChainId.FANTOM: "0x049d68029688eAbF473097a2fC38ef61633A3C7A",
        ChainId.BASE: "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
        ChainId.CRONOS: "0x6614bb4853046ba2ba898d2495b45c26b9c927f8", # Cronos USDT
        ChainId.MOONBEAM: "0xEFAeeE334F0Fd1712f9a8cc15badf99EE59ED547", # Moonbeam USDT
        ChainId.CELO: "0x48065fbBE25f71C9282ddc5e1cD6F6A88F79023f", # Celo USDT
        ChainId.KAVA: "0x919C1c267BC06a7039e03fcc2ef738525769109c", # Kava USDT
    },
    chain_decimals={
        ChainId.BSC: 18,  # Binance-Peg BSC-USD is 18 decimals
        ChainId.FANTOM: 6,
        ChainId.AVALANCHE: 6,
        ChainId.CRONOS: 6,
        ChainId.MOONBEAM: 6,
        ChainId.CELO: 6,
        ChainId.KAVA: 6,
    }
)

USDC = Token(
    symbol="USDC",
    name="USD Coin",
    decimals=6,
    addresses={
        ChainId.ETHEREUM: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        ChainId.BSC: "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
        ChainId.POLYGON: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        ChainId.ARBITRUM: "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8", # Bridged USDC (USDC.e) - Main V2 liquidity
        ChainId.OPTIMISM: "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
        ChainId.AVALANCHE: "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
        ChainId.FANTOM: "0x04068DA6C83AFCFA0e13ba15A6696662335D5B75",
        ChainId.BASE: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        ChainId.ZKSYNC: "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
        ChainId.LINEA: "0x176211869cA2b568f2A7D4EE941E073a821EE1ff",
        ChainId.SCROLL: "0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4",
        ChainId.GNOSIS: "0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83",
        ChainId.CRONOS: "0xc21223249CA28397B4B6541DffAecc539BfF0c59", # Cronos USDC
        ChainId.MOONBEAM: "0x818ec0A7Fe18Ff94269e371a99611F074855e9c9", # Moonbeam USDC
        ChainId.CELO: "0xef4229c8c3250C675F21BCefa426146e195BC086", # Celo USDC
        ChainId.KAVA: "0xfA9343C3897324496A05fC75abeD6bAC29f8A40f", # Kava USDC
    },
    chain_decimals={
        ChainId.BSC: 18,  # Binance-Peg USDC is 18 decimals
    }
)

DAI = Token(
    symbol="DAI",
    name="Dai Stablecoin",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        ChainId.BSC: "0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3",
        ChainId.POLYGON: "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",
        ChainId.ARBITRUM: "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
        ChainId.OPTIMISM: "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
        ChainId.AVALANCHE: "0xd586E7F844cEa2F87f50152665BCbc2C279D8d70",
        ChainId.FANTOM: "0x8D11eC38a3EB5E956B052f67Da8Bdc9bef8Abf3E",
        ChainId.BASE: "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
        ChainId.GNOSIS: "0x44fA8E6f47987339850636F88629646662444217",
    }
)

FRAX = Token(
    symbol="FRAX",
    name="Frax",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0x853d955aCEf822Db058eb8505911ED77F175b99e",
        ChainId.BSC: "0x90C97F71E18723b0Cf0dfa30ee176Ab653E89F40",
        ChainId.POLYGON: "0x45c32fA6DF82ead1e2EF74d17b76547EDdFaFF89",
        ChainId.ARBITRUM: "0x17FC002b466eEc40DaE837Fc4bE5c67993ddBd6F",
        ChainId.OPTIMISM: "0x2E3D870790dC77A83DD1d18184Acc7439A53f475",
        ChainId.AVALANCHE: "0xD24C2Ad096400B6FBcd2ad8B24E7acBc21A1da64",
        ChainId.FANTOM: "0xdc301622e621166BD8E82f2cA0A26c13Ad0BE355",
    }
)

USDD = Token(
    symbol="USDD",
    name="USDD",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0x0C10bF8FcB7Bf5412187A595ab97a3609160b5c6",
        ChainId.BSC: "0xd17479997F34dd9156Deef8F95A52D81D265be9c",
    }
)

TUSD = Token(
    symbol="TUSD",
    name="TrueUSD",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0x0000000000085d4780B73119b644AE5ecd22b376",
        ChainId.BSC: "0x14016E85a25aeb13065688cAFB43044C2ef86784",
    }
)

# ==================== WRAPPED NATIVE TOKENS ====================

WETH = Token(
    symbol="WETH",
    name="Wrapped Ether",
    decimals=18,
    approx_price_usd=3000.0,
    addresses={
        ChainId.ETHEREUM: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        ChainId.BSC: "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",
        ChainId.POLYGON: "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
        ChainId.ARBITRUM: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
        ChainId.OPTIMISM: "0x4200000000000000000000000000000000000006",
        ChainId.AVALANCHE: "0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB",
        ChainId.FANTOM: "0x74b23882a30290451A17c44f4F05243b6b58C76d",
        ChainId.BASE: "0x4200000000000000000000000000000000000006",
        ChainId.ZKSYNC: "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91",
        ChainId.LINEA: "0xe5D7C2a44FfDDf6b295A15c148167daaAf5Cf34f",
        ChainId.SCROLL: "0x5300000000000000000000000000000000000004",
        ChainId.GNOSIS: "0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1",
    }
)

WBNB = Token(
    symbol="WBNB",
    name="Wrapped BNB",
    decimals=18,
    approx_price_usd=600.0,
    addresses={
        ChainId.BSC: "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
        ChainId.ETHEREUM: "0x418D75f65a02b3D53B2418FB8E1fe493759c7605",
    }
)

WMATIC = Token(
    symbol="WMATIC",
    name="Wrapped MATIC",
    decimals=18,
    addresses={
        ChainId.POLYGON: "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
        ChainId.ETHEREUM: "0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0",
    }
)

WAVAX = Token(
    symbol="WAVAX",
    name="Wrapped AVAX",
    decimals=18,
    approx_price_usd=35.0,
    addresses={
        ChainId.AVALANCHE: "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",
        ChainId.ETHEREUM: "0x85f138bfEE4ef8e540890CFb48F620571d67Edd3",
    }
)

WFTM = Token(
    symbol="WFTM",
    name="Wrapped Fantom",
    decimals=18,
    approx_price_usd=0.7,
    addresses={
        ChainId.FANTOM: "0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83",
        ChainId.ETHEREUM: "0x4E15361FD6b4BB609Fa63C81A2be19d873717870",
    }
)

WCRO = Token(
    symbol="WCRO",
    name="Wrapped CRO",
    decimals=18,
    approx_price_usd=0.15,
    addresses={
        ChainId.CRONOS: "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23",
        ChainId.ETHEREUM: "0xA0b73E1Ff0B80914AB6fe0457743b4741C57bD86", # ERC20 CRO
    }
)

WGLMR = Token(
    symbol="WGLMR",
    name="Wrapped GLMR",
    decimals=18,
    approx_price_usd=0.4,
    addresses={
        ChainId.MOONBEAM: "0xAcc15dC74880C9944775448304B263D191c6077F",
    }
)

WCELO = Token(
    symbol="WCELO",
    name="Wrapped Celo",
    decimals=18,
    approx_price_usd=0.8,
    addresses={
        ChainId.CELO: "0x471EcE3750Da237f93b8E339c536989b8978a438",
    }
)

WKAVA = Token(
    symbol="WKAVA",
    name="Wrapped Kava",
    decimals=18,
    approx_price_usd=0.7,
    addresses={
        ChainId.KAVA: "0xc86c7C0eFbd6A49B35e8714C5f59D99De09A225b",
    }
)

ATOM = Token(
    symbol="ATOM",
    name="Cosmos Hub",
    decimals=6,
    approx_price_usd=8.0,
    addresses={
        ChainId.CRONOS: "0xB888d8Dd1733d72681b30c00ee76bDE93ae7aa93", # Bridged ATOM
        ChainId.KAVA: "0x15932E26f5BD4923d46a2b205191C4b5d5f43FE3", # Bridged ATOM
        ChainId.BSC: "0x0Eb3a705fc54725037CC9e008CEDE169F1f17e6B",
    },
    chain_decimals={
        ChainId.BSC: 18,
        ChainId.CRONOS: 6,
        ChainId.KAVA: 6,
    }
)

DOT = Token(
    symbol="DOT",
    name="Polkadot",
    decimals=10,
    approx_price_usd=7.0,
    addresses={
        ChainId.MOONBEAM: "0xFfFFfFff1FcaCBd218EDc0EbA20Fc2308C778080", # xcDOT
        ChainId.BSC: "0x7083609fCE4d1d8Dc0C979AAb8c869Ea2C873402",
    },
    chain_decimals={
        ChainId.BSC: 18,
        ChainId.MOONBEAM: 10,
    }
)

# ==================== MAJOR CRYPTOS ====================

WBTC = Token(
    symbol="WBTC",
    name="Wrapped Bitcoin",
    decimals=8,
    approx_price_usd=65000.0,
    addresses={
        ChainId.ETHEREUM: "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        ChainId.BSC: "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c",
        ChainId.POLYGON: "0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6",
        ChainId.ARBITRUM: "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f",
        ChainId.OPTIMISM: "0x68f180fcCe6836688e9084f035309E29Bf0A2095",
        ChainId.AVALANCHE: "0x50b7545627a5162F82A992c33b87aDc75187B218",
        ChainId.FANTOM: "0x321162Cd933E2Be498Cd2267a90534A804051b11",
    },
    chain_decimals={
        ChainId.BSC: 18,  # Binance-Peg BTCB is 18 decimals
    }
)

# ==================== DEFI TOKENS ====================

LINK = Token(
    symbol="LINK",
    name="Chainlink",
    decimals=18,
    approx_price_usd=20.0,
    addresses={
        ChainId.ETHEREUM: "0x514910771AF9Ca656af840dff83E8264EcF986CA",
        ChainId.BSC: "0xF8A0BF9cF54Bb92F17374d9e9A321E6a111a51bD",
        ChainId.POLYGON: "0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39",
        ChainId.ARBITRUM: "0xf97f4df75117a78c1A5a0DBb814Af92458539FB4",
        ChainId.OPTIMISM: "0x350a791Bfc2C21F9Ed5d10980Dad2e2638ffa7f6",
        ChainId.AVALANCHE: "0x5947BB275c521040051D82396192181b413227A3",
        ChainId.FANTOM: "0xb3654dc3D10Ea7645f8319668E8F54d2574FBdC8",
    }
)

UNI = Token(
    symbol="UNI",
    name="Uniswap",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
        ChainId.BSC: "0xBf5140A22578168FD562DCcF235E5D43A02ce9B1",
        ChainId.POLYGON: "0xb33EaAd8d922B1083446DC23f610c2567fB5180f",
        ChainId.ARBITRUM: "0xFa7F8980b0f1E64A2062791cc3b0871572f1F7f0",
        ChainId.OPTIMISM: "0x6fd9d7AD17242c41f7131d257212c54A0e816691",
        ChainId.AVALANCHE: "0x8eBAf22B6F053dFFeaf46f4Dd9eFA95D89ba8580",
    }
)

AAVE = Token(
    symbol="AAVE",
    name="Aave",
    decimals=18,
    approx_price_usd=100.0,
    addresses={
        ChainId.ETHEREUM: "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
        ChainId.BSC: "0xfb6115445Bff7b52FeB98650C87f44907E58f802",
        ChainId.POLYGON: "0xD6DF932A45C0f255f85145f286eA0b292B21C90B",
        ChainId.ARBITRUM: "0xba5DdD1f9d7F570dc94a51479a000E3BCE967196",
        ChainId.OPTIMISM: "0x76FB31fb4af56892A25e32cFC43De717950c9278",
        ChainId.AVALANCHE: "0x63a72806098Bd3D9520cC43356dD78afe5D386D9",
        ChainId.FANTOM: "0x6a07A792ab2965C72a5B8088d3a069A7aC3a993B",
    }
)

CRV = Token(
    symbol="CRV",
    name="Curve DAO Token",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0xD533a949740bb3306d119CC777fa900bA034cd52",
        ChainId.POLYGON: "0x172370d5Cd63279eFa6d502DAB29171933a610AF",
        ChainId.ARBITRUM: "0x11cDb42B0EB46D95f990BeDD4695A6e3fA034978",
        ChainId.OPTIMISM: "0x0994206dfE8De6Ec6920FF4D779B0d950605Fb53",
        ChainId.AVALANCHE: "0x249848BeCA43aC405b8102Ec90Dd5F22CA513c06",
        ChainId.FANTOM: "0x1E4F97b9f9F913c46F1632781732927B9019C68b",
    }
)

MKR = Token(
    symbol="MKR",
    name="Maker",
    decimals=18,
    approx_price_usd=2000.0,
    addresses={
        ChainId.ETHEREUM: "0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2",
    }
)

SNX = Token(
    symbol="SNX",
    name="Synthetix",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F",
        ChainId.OPTIMISM: "0x8700dAec35aF8Ff88c16BdF0418774CB3D7599B4",
    }
)

COMP = Token(
    symbol="COMP",
    name="Compound",
    decimals=18,
    approx_price_usd=50.0,
    addresses={
        ChainId.ETHEREUM: "0xc00e94Cb662C3520282E6f5717214004A7f26888",
        ChainId.POLYGON: "0x8505b9d2254A7Ae468C0E9dd10Ccea3A837aef5c",
    }
)

LDO = Token(
    symbol="LDO",
    name="Lido DAO",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32",
        ChainId.ARBITRUM: "0x13Ad51ed4F1B7e9Dc168d8a00cB3f4dDD85EfA60",
        ChainId.OPTIMISM: "0xFdb794692724153d1488CcdBE0C56c252596735F",
    }
)

# ==================== LAYER 2 TOKENS ====================

ARB = Token(
    symbol="ARB",
    name="Arbitrum",
    decimals=18,
    approx_price_usd=1.0,
    addresses={
        ChainId.ARBITRUM: "0x912CE59144191C1204E64559FE8253a0e49E6548",
        ChainId.ETHEREUM: "0xB50721BCf8d664c30412Cfbc6cf7a15145234ad1",
    }
)

OP = Token(
    symbol="OP",
    name="Optimism",
    decimals=18,
    approx_price_usd=3.0,
    addresses={
        ChainId.OPTIMISM: "0x4200000000000000000000000000000000000042",
        ChainId.ETHEREUM: "0x4200000000000000000000000000000000000042",
    }
)

MATIC = Token(
    symbol="MATIC",
    name="Polygon",
    decimals=18,
    approx_price_usd=0.6,
    addresses={
        ChainId.ETHEREUM: "0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0",
        ChainId.BSC: "0xCC42724C6683B7E57334c4E856f4c9965ED682bD",
    }
)

# ==================== MEME COINS ====================

SHIB = Token(
    symbol="SHIB",
    name="Shiba Inu",
    decimals=18,
    approx_price_usd=0.00002,
    addresses={
        ChainId.ETHEREUM: "0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE",
        ChainId.BSC: "0x2859e4544C4bB03966803b044A93563Bd2D0DD4D",
    }
)

PEPE = Token(
    symbol="PEPE",
    name="Pepe",
    decimals=18,
    approx_price_usd=0.000002,
    addresses={
        ChainId.ETHEREUM: "0x6982508145454Ce325dDbE47a25d4ec3d2311933",
        ChainId.BSC: "0x25d887Ce7a35172C62FeBFD67a1856F20FaEbB00",
    }
)

DOGE = Token(
    symbol="DOGE",
    name="Dogecoin (Bridged)",
    decimals=8,
    approx_price_usd=0.15,
    addresses={
        ChainId.BSC: "0xbA2aE424d960c26247Dd6c32edC70B295c744C43",
    }
)

FLOKI = Token(
    symbol="FLOKI",
    name="Floki",
    decimals=9,
    addresses={
        ChainId.ETHEREUM: "0xcf0C122c6b73ff809C693DB761e7BaeBe62b6a2E",
        ChainId.BSC: "0xfb5B838b6cfEEdC2873aB27866079AC55363D37E",
    }
)

# ==================== GAMING / METAVERSE ====================

APE = Token(
    symbol="APE",
    name="ApeCoin",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0x4d224452801ACEd8B2F0aebebAC0Ff96D3c5e1e4",
    }
)

SAND = Token(
    symbol="SAND",
    name="The Sandbox",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0x3845badAde8e6dFF049820680d1F14bD3903a5d0",
        ChainId.BSC: "0x67b725d7e342d7B611fa85e859Df9697D9378B2e",
        ChainId.POLYGON: "0xBbba073C31bF03b8ACf7c28EF0738DeCF3695683",
    }
)

MANA = Token(
    symbol="MANA",
    name="Decentraland",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0x0F5D2fB29fb7d3CFeE444a200298f468908cC942",
        ChainId.BSC: "0x26433c8127d9b4e9B71Eaa15111DF99Ea2EeB2f8",
        ChainId.POLYGON: "0xA1c57f48F0Deb89f569dFbE6E2B7f46D33606fD4",
    }
)

AXS = Token(
    symbol="AXS",
    name="Axie Infinity",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b",
        ChainId.BSC: "0x715D400F88C167884bbCc41C5FeA407ed4D2f8A0",
    }
)

# ==================== AI TOKENS ====================

FET = Token(
    symbol="FET",
    name="Fetch.ai",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0xaea46A60368A7bD060eec7DF8CBa43b7EF41Ad85",
        ChainId.BSC: "0x031b41e504677879370e9DBcF937283A8691Fa7f",
    }
)

AGIX = Token(
    symbol="AGIX",
    name="SingularityNET",
    decimals=8,
    addresses={
        ChainId.ETHEREUM: "0x5B7533812759B45C2B44C19e320ba2cD2681b542",
    }
)

OCEAN = Token(
    symbol="OCEAN",
    name="Ocean Protocol",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0x967da4048cD07aB37855c090aAF366e4ce1b9F48",
        ChainId.BSC: "0xDCe07662CA8EbC241316a15B611c89711414Dd1a",
        ChainId.POLYGON: "0x282d8efCe846A88B159800bd4130ad77443Fa1A1",
    }
)

# ==================== INFRASTRUCTURE ====================

GRT = Token(
    symbol="GRT",
    name="The Graph",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0xc944E90C64B2c07662A292be6244BDf05Cda44a7",
        ChainId.ARBITRUM: "0x9623063377AD1B27544C965cCd7342f7EA7e88C7",
    }
)

FIL = Token(
    symbol="FIL",
    name="Filecoin (Bridged)",
    decimals=18,
    addresses={
        ChainId.BSC: "0x0D8Ce2A99Bb6e3B7Db580eD848240e4a0F9aE153",
    }
)

STX = Token(
    symbol="STX",
    name="Stacks (Bridged)",
    decimals=6,
    addresses={
        ChainId.BSC: "0xaEbCEebf90a40a64c54C7fB9B86fe72cC9C0C9c7",
    }
)

INJ = Token(
    symbol="INJ",
    name="Injective",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0xe28b3B32B6c345A34Ff64674606124Dd5Aceca30",
        ChainId.BSC: "0xa2B726B1145A4773F68593CF171187d8EBe4d495",
    }
)

RUNE = Token(
    symbol="RUNE",
    name="THORChain",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0x3155BA85D5F96b2d030a4966AF206230e46849cb",
        ChainId.BSC: "0xA9B1Eb5908CfC3cdf91F9B8B3a74108598009096",
    }
)

# ==================== STAKING TOKENS ====================

STETH = Token(
    symbol="stETH",
    name="Lido Staked ETH",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",
    }
)

RETH = Token(
    symbol="rETH",
    name="Rocket Pool ETH",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0xae78736Cd615f374D3085123A210448E74Fc6393",
        ChainId.ARBITRUM: "0xEC70Dcb4A1EFa46b8F2D97C310C9c4790ba5ffA8",
        ChainId.OPTIMISM: "0x9Bcef72be871e61ED4fBbc7630889beE758eb81D",
    }
)

CBETH = Token(
    symbol="cbETH",
    name="Coinbase Staked ETH",
    decimals=18,
    addresses={
        ChainId.ETHEREUM: "0xBe9895146f7AF43049ca1c1AE358B0541Ea49704",
        ChainId.BASE: "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22",
    }
)


# All tokens list
ALL_TOKENS: list[Token] = [
    # Stablecoins
    USDT, USDC, DAI, FRAX, USDD, TUSD,
    # Wrapped Native
    WETH, WBNB, WMATIC, WAVAX, WFTM,
    # Major
    WBTC,
    # DeFi
    LINK, UNI, AAVE, CRV, MKR, SNX, COMP, LDO,
    # L2
    ARB, OP, MATIC,
    # Meme
    SHIB, PEPE, DOGE, FLOKI,
    # Gaming
    APE, SAND, MANA, AXS,
    # AI
    FET, AGIX, OCEAN,
    # Infrastructure
    GRT, FIL, STX, INJ, RUNE,
    # Staking
    STETH, RETH, CBETH,
    # New Chains
    WCRO, WGLMR, WCELO, WKAVA, ATOM, DOT,
]

# Expanded trading pairs (base/quote)
TRADING_PAIRS: list[tuple[str, str]] = [
    # Major pairs
    ("ETH", "USDT"), ("ETH", "USDC"), ("ETH", "DAI"),
    ("BTC", "USDT"), ("BTC", "USDC"), ("BTC", "ETH"),
    ("BNB", "USDT"), ("BNB", "USDC"),
    ("MATIC", "USDT"), ("MATIC", "USDC"),
    ("AVAX", "USDT"), ("AVAX", "USDC"),
    ("FTM", "USDT"),
    
    # DeFi pairs
    ("LINK", "USDT"), ("LINK", "ETH"),
    ("UNI", "USDT"), ("UNI", "ETH"),
    ("AAVE", "USDT"), ("AAVE", "ETH"),
    ("CRV", "USDT"), ("CRV", "ETH"),
    ("MKR", "USDT"), ("MKR", "ETH"),
    ("SNX", "USDT"),
    ("COMP", "USDT"),
    ("LDO", "USDT"), ("LDO", "ETH"),
    
    # L2 pairs
    ("ARB", "USDT"), ("ARB", "ETH"),
    ("OP", "USDT"), ("OP", "ETH"),
    
    # New Chain pairs
    ("CRO", "USDT"), ("CRO", "USDC"),
    ("GLMR", "USDT"), ("GLMR", "USDC"),
    ("CELO", "USDT"), ("CELO", "USDC"),
    ("KAVA", "USDT"), ("KAVA", "USDC"),
    ("ATOM", "USDT"), ("ATOM", "USDC"),
    ("DOT", "USDT"), ("DOT", "USDC"),
    
    # Meme pairs
    ("SHIB", "USDT"),
    ("PEPE", "USDT"), ("PEPE", "ETH"),
    ("DOGE", "USDT"),
    ("FLOKI", "USDT"),
    
    # Gaming pairs
    ("APE", "USDT"), ("APE", "ETH"),
    ("SAND", "USDT"),
    ("MANA", "USDT"),
    ("AXS", "USDT"),
    
    # AI pairs
    ("FET", "USDT"),
    ("AGIX", "USDT"),
    ("OCEAN", "USDT"),
    
    # Infrastructure pairs
    ("GRT", "USDT"),
    ("INJ", "USDT"),
    ("RUNE", "USDT"),
    
    # Staking pairs
    ("stETH", "ETH"),
    ("rETH", "ETH"),
    ("cbETH", "ETH"),
    
    # Cross pairs
    ("ETH", "BTC"),
    ("BNB", "ETH"),
    ("LINK", "BTC"),
]

# CEX symbol mapping (normalize symbols)
CEX_SYMBOL_MAP: dict[str, str] = {
    "WETH": "ETH",
    "WBTC": "BTC",
    "WBNB": "BNB",
    "WMATIC": "MATIC",
    "WAVAX": "AVAX",
    "WFTM": "FTM",
    "stETH": "STETH",
    "rETH": "RETH",
    "cbETH": "CBETH",
    "WCRO": "CRO",
    "WGLMR": "GLMR",
    "WCELO": "CELO",
    "WKAVA": "KAVA",
}


def get_tokens_for_chain(chain_id: ChainId) -> list[Token]:
    """Get all tokens available on a specific chain"""
    return [t for t in ALL_TOKENS if chain_id in t.addresses]


def normalize_symbol(symbol: str) -> str:
    """Normalize wrapped token symbols to their base form for CEX comparison"""
    return CEX_SYMBOL_MAP.get(symbol, symbol)
