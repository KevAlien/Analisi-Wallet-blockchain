"""
API client for blockchain explorer APIs (Etherscan, Arbiscan)
"""
from typing import Dict, List, Any, Optional
import logging
import time
import requests

from src.config.settings import ETHERSCAN_API_KEY, ARBISCAN_API_KEY
from src.config.wallet_registry import Chain

# Configure logger
logger = logging.getLogger(__name__)

class ExplorerAPIClient:
    """Client for interacting with blockchain explorer APIs"""
    
    BASE_URLS = {
        Chain.ETHEREUM: "https://api.etherscan.io/api",
        Chain.ARBITRUM: "https://api.arbiscan.io/api"
    }
    
    API_KEYS = {
        Chain.ETHEREUM: ETHERSCAN_API_KEY,
        Chain.ARBITRUM: ARBISCAN_API_KEY
    }
    
    def __init__(self):
        """Initialize the explorer API client"""
        self.session = requests.Session()
        
        # Check if API keys are configured
        for chain, api_key in self.API_KEYS.items():
            if not api_key:
                logger.warning(f"No API key configured for {chain.value}")
    
    def _make_request(
        self, 
        chain: Chain, 
        action: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the explorer API
        
        Args:
            chain: The blockchain to query
            action: API action to perform
            params: Additional parameters for the request
            
        Returns:
            API response data
        """
        base_url = self.BASE_URLS.get(chain)
        api_key = self.API_KEYS.get(chain)
        
        if not base_url or not api_key:
            logger.error(f"Missing configuration for {chain.value}")
            return {"status": "0", "message": "Missing API configuration"}
        
        # Build request parameters
        request_params = {
            "module": "account" if "txlist" in action else "proxy",
            "action": action,
            "apikey": api_key
        }
        
        if params:
            request_params.update(params)
            
        try:
            response = self.session.get(base_url, params=request_params)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if data.get("status") == "0" and data.get("message") != "No transactions found":
                logger.warning(f"API error: {data.get('message')} for {chain.value}")
            
            # Add a delay to respect rate limits
            time.sleep(0.2)
            
            return data
        
        except requests.RequestException as e:
            logger.error(f"Request error for {chain.value}: {str(e)}")
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
