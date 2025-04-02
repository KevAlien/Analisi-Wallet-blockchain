"""
Wallet registry for tracking whale and market maker addresses
"""
from enum import Enum
from typing import Dict, List, Optional

class WalletCategory(Enum):
    """Categories for wallet classification"""
    WHALE = "whale"
    MARKET_MAKER = "market_maker"
    EXCHANGE = "exchange"
    DEFI_PROTOCOL = "defi_protocol"
    OTHER = "other"

class Chain(Enum):
    """Supported blockchain networks"""
    ETHEREUM = "ethereum"
    ARBITRUM = "arbitrum"

class WalletInfo:
    """Information about a wallet to be tracked"""
    def __init__(
        self,
        address: str,
        category: WalletCategory,
        name: Optional[str] = None,
        description: Optional[str] = None,
        chains: Optional[List[Chain]] = None,
        tags: Optional[List[str]] = None,
        threshold_override: Optional[float] = None
    ):
        self.address = address.lower()  # Normalize to lowercase
        self.category = category
        self.name = name
        self.description = description
        self.chains = chains or [Chain.ETHEREUM, Chain.ARBITRUM]  # Default to all chains
        self.tags = tags or []
        self.threshold_override = threshold_override  # Custom threshold for this wallet
    
    def __str__(self) -> str:
        return f"{self.name or 'Unnamed'} ({self.address[:8]}...{self.address[-6:]})"

# Registry of wallets to monitor
WHALE_WALLETS: List[WalletInfo] = [
    # Example whale wallets to track - replace with actual addresses
    WalletInfo(
        address="0x28c6c06298d514db089934071355e5743bf21d60",
        category=WalletCategory.WHALE,
        name="Binance 14",
        description="Binance hot wallet",
        tags=["exchange", "binance"]
    ),
    WalletInfo(
        address="0x5a52e96bacdabb82fd05763e25335261b270efcb",
        category=WalletCategory.WHALE,
        name="Alameda Research",
        tags=["trading_firm"]
    ),
]

MARKET_MAKER_WALLETS: List[WalletInfo] = [
    # Example market maker wallets - replace with actual addresses
    WalletInfo(
        address="0x000000000dfde7deaf24138722987c9a6991e2d4",
        category=WalletCategory.MARKET_MAKER,
        name="Wintermute",
        tags=["mm", "trading_firm"]
    ),
]

EXCHANGE_WALLETS: List[WalletInfo] = [
    # Example exchange wallets - replace with actual addresses
    WalletInfo(
        address="0x742d35cc6634c0532925a3b844bc454e4438f44e",
        category=WalletCategory.EXCHANGE,
        name="Coinbase",
        tags=["exchange", "coinbase"]
    ),
]

# Combined registry of all wallets to track
ALL_WALLETS: List[WalletInfo] = [
    *WHALE_WALLETS,
    *MARKET_MAKER_WALLETS,
    *EXCHANGE_WALLETS,
]

# Dictionary for quick lookups by address
WALLET_BY_ADDRESS: Dict[str, WalletInfo] = {
    wallet.address: wallet for wallet in ALL_WALLETS
}

def get_wallet_by_address(address: str) -> Optional[WalletInfo]:
    """
    Lookup a wallet by address
    
    Args:
        address: The wallet address to lookup
        
    Returns:
        WalletInfo object if found, None otherwise
    """
    return WALLET_BY_ADDRESS.get(address.lower())

def get_wallets_by_category(category: WalletCategory) -> List[WalletInfo]:
    """
    Get all wallets of a specific category
    
    Args:
        category: The category to filter by
        
    Returns:
        List of WalletInfo objects with the specified category
    """
    return [wallet for wallet in ALL_WALLETS if wallet.category == category]

def get_wallets_by_tag(tag: str) -> List[WalletInfo]:
    """
    Get all wallets that have a specific tag
    
    Args:
        tag: The tag to filter by
        
    Returns:
        List of WalletInfo objects with the specified tag
    """
    return [wallet for wallet in ALL_WALLETS if tag in wallet.tags]
