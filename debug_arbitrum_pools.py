
import asyncio
from web3 import AsyncWeb3
from eth_abi import decode

# Config
ARBITRUM_RPC = "https://arbitrum.drpc.org"
SUSHISWAP_V2_FACTORY = "0xc35DADB65012eC5796536bD9864eD8773aBc74C4" # Wait, checking config... 
# config/chains.py says: 0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506 (Scanner uses this for Sushi)
# Let's use the one from config/chains.py
SUSHISWAP_ROUTER = "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506"

# Tokens
WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
USDC_NATIVE = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
USDC_BRIDGED = "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8"

# ABIs
FACTORY_ABI = [{"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"}],"name":"getPair","outputs":[{"internalType":"address","name":"pair","type":"address"}],"stateMutability":"view","type":"function"}]
PAIR_ABI = [{"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"token0","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}]
ROUTER_ABI = [{"inputs":[],"name":"factory","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}]

async def check_pair(name, token_a, token_b, router_address, web3):
    print(f"\n--- Checking {name} ---")
    router_contract = web3.eth.contract(address=web3.to_checksum_address(router_address), abi=ROUTER_ABI)
    factory_address = await router_contract.functions.factory().call()
    print(f"Factory: {factory_address}")
    
    factory_contract = web3.eth.contract(address=factory_address, abi=FACTORY_ABI)
    pair_address = await factory_contract.functions.getPair(web3.to_checksum_address(token_a), web3.to_checksum_address(token_b)).call()
    
    print(f"Pair Address: {pair_address}")
    
    if pair_address == "0x0000000000000000000000000000000000000000":
        print("Pair does not exist!")
        return
        
    pair_contract = web3.eth.contract(address=pair_address, abi=PAIR_ABI)
    reserves = await pair_contract.functions.getReserves().call()
    token0 = await pair_contract.functions.token0().call()
    
    # Identify reserves
    if token0.lower() == token_a.lower():
        res_a, res_b = reserves[0], reserves[1]
    else:
        res_a, res_b = reserves[1], reserves[0]
        
    print(f"Reserves A (WETH): {res_a / 10**18:.4f}")
    if "Native" in name:
        print(f"Reserves B (USDC): {res_b / 10**6:.4f}")
    else:
        print(f"Reserves B (USDC.e): {res_b / 10**6:.4f}")
        
    # Price
    if res_a > 0 and res_b > 0:
        price = res_b / res_a * (10**18 / 10**6)
        print(f"Price: {price:.4f} USDC/ETH")
        
        # Invert
        print(f"Startled? 1 ETH = {price:.2f} USDC")
    else:
        print("Empty pool!")

async def main():
    web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(ARBITRUM_RPC))
    
    await check_pair("WETH / USDC (Native) on Sushi", WETH, USDC_NATIVE, SUSHISWAP_ROUTER, web3)
    await check_pair("WETH / USDC.e (Bridged) on Sushi", WETH, USDC_BRIDGED, SUSHISWAP_ROUTER, web3)

if __name__ == "__main__":
    asyncio.run(main())
