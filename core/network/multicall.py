"""
Multicall3 Implementation
Allows batching multiple smart contract read calls into a single RPC request.
Contract Address (All Chains): 0xcA11bde05977b3631167028862bE2a173976CA11
"""
import asyncio
from typing import NamedTuple, Any
from web3 import AsyncWeb3
from eth_abi import decode

MULTICALL3_ADDRESS = "0xcA11bde05977b3631167028862bE2a173976CA11"

MULTICALL3_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "target", "type": "address"},
                    {"internalType": "bool", "name": "allowFailure", "type": "bool"},
                    {"internalType": "bytes", "name": "callData", "type": "bytes"}
                ],
                "internalType": "struct Multicall3.Call3[]",
                "name": "calls",
                "type": "tuple[]"
            }
        ],
        "name": "aggregate3",
        "outputs": [
            {
                "components": [
                    {"internalType": "bool", "name": "success", "type": "bool"},
                    {"internalType": "bytes", "name": "returnData", "type": "bytes"}
                ],
                "internalType": "struct Multicall3.Result[]",
                "name": "returnData",
                "type": "tuple[]"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

class Call(NamedTuple):
    target: str
    allow_failure: bool
    call_data: bytes
    output_types: list[str]  # e.g. ['uint256', 'uint256']

class Multicall:
    def __init__(self, web3: AsyncWeb3):
        self.web3 = web3
        self.contract = web3.eth.contract(
            address=MULTICALL3_ADDRESS,
            abi=MULTICALL3_ABI
        )

    async def aggregate(self, calls: list[Call]) -> list[Any]:
        """
        Execute multiple calls in a single RPC request.
        Returns a list of decoded results. If a call failed (and allow_failure=True), 
        the result will be None.
        """
        if not calls:
            return []

        # Prepare input data
        call_structs = [
            (
                self.web3.to_checksum_address(call.target),
                call.allow_failure,
                call.call_data
            )
            for call in calls
        ]

        # Execute aggregate3
        try:
            results = await self.contract.functions.aggregate3(call_structs).call()
        except Exception as e:
            # Fallback or specific error handling could go here
            # For now, re-raise to handle upstream
            raise e

        decoded_results = []
        for i, (success, return_data) in enumerate(results):
            if not success or not return_data:
                decoded_results.append(None)
                continue
            
            try:
                # Decode the result bytes
                decoded = decode(calls[i].output_types, return_data)
                # Unwrap single values
                if len(decoded) == 1:
                    decoded_results.append(decoded[0])
                else:
                    decoded_results.append(decoded)
            except Exception:
                decoded_results.append(None)

        return decoded_results
