"""
API client for blockchain explorer APIs using Etherscan API V2
Migrated to V2 unified endpoint with chainid parameter support
"""
from typing import Dict, List, Any, Optional
import logging

import requests

from src.config.settings import ETHERSCAN_API_KEY
from src.config.wallet_registry import Chain

# Configure logger
logger = logging.getLogger(__name__)

class ExplorerAPIClient:
    """Client for interacting with Etherscan API V2 (unified multichain endpoint)"""

    # V2 uses a single unified base URL
    BASE_URL = "https://api.etherscan.io/v2/api"

    # Chain ID mapping for V2 API
    CHAIN_IDS = {
        Chain.ETHEREUM: 1,
        Chain.ARBITRUM: 42161
    }
    
    def __init__(self):
        """Initialize the explorer API client"""
        self.session = requests.Session()

        # Check if API key is configured (V2 uses single key for all chains)
        if not ETHERSCAN_API_KEY:
            logger.warning("No Etherscan API key configured. Set ETHERSCAN_API_KEY in your environment.")
    
    def _make_request(
        self,
        chain: Chain,
        action: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the Etherscan API V2

        Args:
            chain: The blockchain to query
            action: API action to perform
            params: Additional parameters for the request

        Returns:
            API response data
        """
        # Get chainid for the specified chain
        chain_id = self.CHAIN_IDS.get(chain)

        if not chain_id:
            logger.error(f"Unsupported chain: {chain.value}")
            return {"status": "0", "message": f"Unsupported chain: {chain.value}"}

        if not ETHERSCAN_API_KEY:
            logger.error("Missing Etherscan API key")
            return {"status": "0", "message": "Missing API key"}

        # Build request parameters for V2 API
        request_params = {
            "chainid": chain_id,  # V2 requires chainid parameter
            "module": "account" if "txlist" in action else "proxy",
            "action": action,
            "apikey": ETHERSCAN_API_KEY
        }

        if params:
            request_params.update(params)

        try:
            response = self.session.get(self.BASE_URL, params=request_params)
            response.raise_for_status()

            data = response.json()

            # Check for API errors
            if data.get("status") == "0" and data.get("message") != "No transactions found":
                logger.warning(f"API error: {data.get('message')} for {chain.value} (chainid={chain_id})")

            return data

        except requests.RequestException as e:
            logger.error(f"Request error for {chain.value} (chainid={chain_id}): {str(e)}")
            return {"status": "0", "message": f"Request error: {str(e)}"}
    
    def get_wallet_transactions(
        self, 
        address: str, 
        chain: Chain, 
        start_block: int = 0, 
        end_block: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = "desc"
    ) -> List[Dict[str, Any]]:
        """
        Get transactions for a wallet address
        
        Args:
            address: Wallet address to check
            chain: The blockchain to query
            start_block: Starting block
            end_block: Ending block
            page: Page number
            offset: Number of results per page
            sort: Sort direction ('asc' or 'desc')
            
        Returns:
            List of transactions
        """
        params = {
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": offset,
            "sort": sort
        }
        
        response = self._make_request(chain, "txlist", params)
        
        if response.get("status") == "1":
            return response.get("result", [])
        
        # Handle "No transactions found" gracefully
        if response.get("message") == "No transactions found":
            return []
            
        logger.warning(f"Failed to get transactions for {address} on {chain.value}: {response.get('message')}")
        return []
    
    def get_token_transfers(
        self,
        address: str,
        chain: Chain,
        contract_address: Optional[str] = None,
        start_block: int = 0,
        end_block: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = "desc"
    ) -> List[Dict[str, Any]]:
        """
        Get token transfers for a wallet address
        
        Args:
            address: Wallet address to check
            chain: The blockchain to query
            contract_address: Specific ERC20 token contract (optional)
            start_block: Starting block
            end_block: Ending block
            page: Page number
            offset: Number of results per page
            sort: Sort direction ('asc' or 'desc')
            
        Returns:
            List of token transfers
        """
        params = {
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": offset,
            "sort": sort
        }
        
        if contract_address:
            params["contractaddress"] = contract_address
            action = "tokentx"  # ERC20 token transfers
        else:
            action = "tokentx"  # All token transfers
            
        response = self._make_request(chain, action, params)
        
        if response.get("status") == "1":
            return response.get("result", [])
            
        # Handle "No transactions found" gracefully
        if response.get("message") == "No transactions found":
            return []
            
        logger.warning(f"Failed to get token transfers for {address} on {chain.value}: {response.get('message')}")
        return []
    
    def get_internal_transactions(
        self,
        address: str,
        chain: Chain,
        start_block: int = 0,
        end_block: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = "desc"
    ) -> List[Dict[str, Any]]:
        """
        Get internal transactions for a wallet address
        
        Args:
            address: Wallet address to check
            chain: The blockchain to query
            start_block: Starting block
            end_block: Ending block
            page: Page number
            offset: Number of results per page
            sort: Sort direction ('asc' or 'desc')
            
        Returns:
            List of internal transactions
        """
        params = {
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": offset,
            "sort": sort
        }
        
        response = self._make_request(chain, "txlistinternal", params)
        
        if response.get("status") == "1":
            return response.get("result", [])
            
        # Handle "No transactions found" gracefully
        if response.get("message") == "No transactions found":
            return []
            
        logger.warning(f"Failed to get internal transactions for {address} on {chain.value}: {response.get('message')}")
        return []
