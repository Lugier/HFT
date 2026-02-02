"""
DEX Executor for handling on-chain swaps
"""
import time
from web3 import AsyncWeb3

from config.chains import ChainId
from config.secrets import secret_manager
from utils.rpc_manager import rpc_manager
from utils.logger import get_logger

logger = get_logger(__name__)

# Standard ERC20 ABI for approval/transfer
ERC20_ABI = [
    {
        "constant": False,
        "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    }
]

# Uniswap V2 Router Swap ABI
ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

class DEXExecutor:
    """
    Handles DEX execution (Approvals, Swaps)
    """
    
    def __init__(self, chain_id: ChainId):
        self.chain_id = chain_id
        self.private_key = secret_manager.get_private_key()
        self._web3: AsyncWeb3 | None = None
        self._account = None
        
        if self.private_key:
            try:
                # Initialize account
                # Note: We need a temporary sync web3 to derive account from key? 
                # Or just use eth_account.
                from eth_account import Account
                self._account = Account.from_key(self.private_key)
                logger.info(f"DEX Execution initialized for wallet: {self._account.address[:6]}...{self._account.address[-4:]}")
            except Exception as e:
                logger.error(f"Failed to initialize wallet: {e}")
    
    async def _get_web3(self) -> AsyncWeb3:
        if self._web3 is None:
            self._web3 = await rpc_manager.get_web3(self.chain_id)
        return self._web3
        
    async def approve_token(
        self, 
        token_address: str, 
        spender_address: str, 
        amount: int = 2**256 - 1
    ) -> str | None:
        """
        Approve a spender to spend tokens. 
        Returns transaction hash if submitted, None if failed/already approved.
        """
        if not self._account:
            return None
            
        try:
            web3 = await self._get_web3()
            contract = web3.eth.contract(address=web3.to_checksum_address(token_address), abi=ERC20_ABI)
            spender = web3.to_checksum_address(spender_address)
            
            # Check allowance first
            allowance = await contract.functions.allowance(self._account.address, spender).call()
            if allowance >= amount:
                logger.debug(f"Allowance already sufficient for {token_address}")
                return "0x_ALREADY_APPROVED"
            
            # Build Tx
            nonce = await web3.eth.get_transaction_count(self._account.address)
            gas_price = await web3.eth.gas_price
            
            tx = await contract.functions.approve(spender, amount).build_transaction({
                'from': self._account.address,
                'nonce': nonce,
                'gas': 60000,
                'gasPrice': int(gas_price * 1.1), # 10% tip
                'chainId': self.chain_id.value
            })
            
            # Sign & Send
            signed_tx = web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = await web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            logger.info(f"Submitted Approval: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"Approval failed: {e}")
            return None

    async def execute_swap(
        self,
        router_address: str,
        token_in: str,
        token_out: str,
        amount_in: int,
        min_amount_out: int,
        to_address: str = None
    ) -> str | None:
        """
        Execute a swap on a V2 Router
        """
        if not self._account:
            return None
            
        try:
            web3 = await self._get_web3()
            contract = web3.eth.contract(address=web3.to_checksum_address(router_address), abi=ROUTER_ABI)
            
            if to_address is None:
                to_address = self._account.address
            
            path = [web3.to_checksum_address(token_in), web3.to_checksum_address(token_out)]
            deadline = int(time.time()) + 300  # 5 minutes from now
            
            # Build Tx
            nonce = await web3.eth.get_transaction_count(self._account.address)
            gas_price = await web3.eth.gas_price
            
            # Estimate gas
            try:
                gas_est = await contract.functions.swapExactTokensForTokens(
                    amount_in, min_amount_out, path, to_address, deadline
                ).estimate_gas({'from': self._account.address})
                gas_limit = int(gas_est * 1.2) # 20% buffer
            except Exception:
                gas_limit = 250000  # Safety fallback
            
            tx = await contract.functions.swapExactTokensForTokens(
                amount_in, 
                min_amount_out, 
                path, 
                to_address, 
                deadline
            ).build_transaction({
                'from': self._account.address,
                'nonce': nonce,
                'gas': gas_limit,
                'gasPrice': int(gas_price * 1.1),
                'chainId': self.chain_id.value
            })
            
            # Sign & Send
            signed_tx = web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = await web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            logger.info(f"Submitted Swap: {tx_hash.hex()}")
            return tx_hash.hex()

        except Exception as e:
            logger.error(f"Swap failed: {e}")
            return None
