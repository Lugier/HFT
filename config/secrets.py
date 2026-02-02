"""
Secret Manager for handling sensitive keys
Loads configuration from environment variables or .env file
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load .env file
load_dotenv()

@dataclass
class CEXCredentials:
    api_key: str
    secret: str
    passphrase: Optional[str] = None

class SecretManager:
    """
    Manages access to sensitive credentials
    """
    
    def get_private_key(self) -> str | None:
        """Get wallet private key"""
        return os.getenv("PRIVATE_KEY")
    
    def get_cex_credentials(self, exchange_id: str) -> CEXCredentials | None:
        """Get API credentials for an exchange"""
        prefix = exchange_id.upper()
        
        api_key = os.getenv(f"{prefix}_API_KEY")
        secret = os.getenv(f"{prefix}_SECRET")
        passphrase = os.getenv(f"{prefix}_PASSPHRASE")
        
        if api_key and secret:
            return CEXCredentials(api_key, secret, passphrase)
        
        return None
        
    def is_dry_run(self) -> bool:
        """Check if running in dry run mode"""
        return os.getenv("DRY_RUN", "True").lower() == "true"
    
    def get_max_trade_amount(self) -> float:
        """Get maximum trade amount safety limit"""
        try:
            return float(os.getenv("MAX_TRADE_AMOUNT_USD", "15.0"))
        except:
            return 15.0

# Global instance
secret_manager = SecretManager()
