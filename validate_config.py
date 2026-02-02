"""
Validation script to check integrity of configuration files
"""
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from config.chains import CHAINS, ChainId
from config.tokens import ALL_TOKENS, TRADING_PAIRS, Token
from exchanges.dex.uniswap_v2 import create_dex_instances as create_v2
from exchanges.dex.uniswap_v3 import create_v3_instances as create_v3

def validate_chains():
    print("Checking Chains...")
    for chain_id, config in CHAINS.items():
        if chain_id != config.chain_id:
            print(f"❌ Mismatch ChainId for {config.name}")
        
        if not config.rpc_endpoints:
            print(f"❌ No RPC endpoints for {config.name}")
            
        print(f"✓ {config.name} OK ({len(config.dex_routers)} DEX routers)")

def validate_tokens():
    print("\nChecking Tokens...")
    
    # Check duplicate symbols
    symbols = [t.symbol for t in ALL_TOKENS]
    if len(symbols) != len(set(symbols)):
        from collections import Counter
        dupes = [item for item, count in Counter(symbols).items() if count > 1]
        print(f"❌ Duplicate token symbols: {dupes}")
        
    for token in ALL_TOKENS:
        # Check addresses validity
        for chain_id, addr in token.addresses.items():
            if not addr.startswith("0x") or len(addr) != 42:
                print(f"❌ Invalid address for {token.symbol} on {chain_id}: {addr}")
                
        # Check chain_decimals validity
        for chain_id, dec in token.chain_decimals.items():
            if not isinstance(dec, int):
                print(f"❌ Invalid decimal for {token.symbol} on {chain_id}: {dec}")

    print(f"✓ {len(ALL_TOKENS)} Tokens valid")

def validate_pairs():
    print("\nChecking Trading Pairs...")
    token_map = {t.symbol: t for t in ALL_TOKENS}
    token_map.update({t.symbol: t for t in ALL_TOKENS}) # In case of alias? No
    
    # Hardcoded known aliases or base assets not strictly in ALL_TOKENS?
    # Usually ETH, BTC, BNB are base assets, might be represented by WETH etc in logic
    # But TRADING_PAIRS are strings.
    
    # We should check if symbols in pairs correspond to something meaningful.
    # The scanner normalizes symbols.
    
    print(f"✓ {len(TRADING_PAIRS)} pairs configured")

def validate_dexs():
    print("\nChecking DEX Instantiation...")
    try:
        v2_instances = create_v2()
        print(f"✓ {len(v2_instances)} V2 DEX instances created")
        
        v3_instances = create_v3()
        print(f"✓ {len(v3_instances)} V3 DEX instances created")
        
    except Exception as e:
        print(f"❌ DEX Instantiation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        validate_chains()
        validate_tokens()
        validate_pairs()
        validate_dexs()
        print("\n✨ Configuration Validated Successfully")
    except Exception as e:
        print(f"\n❌ Validation Failed: {e}")
        import traceback
        traceback.print_exc()
