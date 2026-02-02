import asyncio
from web3 import AsyncWeb3
from exchanges.dex.base_dex import UNISWAP_V2_ROUTER_ABI

async def main():
    # Arbitrum RPC
    rpc = "https://arb1.arbitrum.io/rpc"
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc))
    
    # SushiSwap Arbitrum Router
    router_addr = "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506"
    router = w3.eth.contract(address=w3.to_checksum_address(router_addr), abi=UNISWAP_V2_ROUTER_ABI)
    
    # Tokens
    link = w3.to_checksum_address("0xf97f4df75117a78c1A5a0DBb814Af92458539FB4")
    usdt = w3.to_checksum_address("0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9")
    
    amount_in = 10**18 # 1 LINK
    
    try:
        amounts = await router.functions.getAmountsOut(amount_in, [link, usdt]).call()
        print(f"Raw amounts: {amounts}")
        print(f"LINK (18 dec) -> USDT (6 dec)")
        print(f"1 LINK = {amounts[1] / 10**6} USDT")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
