# Etherscan API V2 Migration

## Overview

This project has been successfully migrated from Etherscan API V1 to V2. The migration was completed to comply with Etherscan's deprecation of V1 endpoints (deadline: May 31, 2025).

## Key Changes

### 1. Unified API Endpoint
- **Before (V1)**: Separate endpoints per chain
  - Ethereum: `https://api.etherscan.io/api`
  - Arbitrum: `https://api.arbiscan.io/api`
- **After (V2)**: Single unified endpoint
  - All chains: `https://api.etherscan.io/v2/api`

### 2. Chain Identification via ChainID Parameter
V2 requires a `chainid` parameter in all API requests:
- Ethereum: `chainid=1`
- Arbitrum: `chainid=42161`

### 3. Single API Key for All Chains
- **Before (V1)**: Required separate API keys
  - `ETHERSCAN_API_KEY` for Ethereum
  - `ARBISCAN_API_KEY` for Arbitrum
- **After (V2)**: Single API key works across all 60+ supported chains
  - Only `ETHERSCAN_API_KEY` is needed

## Files Modified

### Code Changes
1. **src/fetching/explorer_api.py**
   - Updated to use V2 unified endpoint
   - Added `CHAIN_IDS` mapping for supported chains
   - Modified `_make_request()` to include `chainid` parameter
   - Removed dependency on chain-specific API keys

2. **src/config/settings.py**
   - Added deprecation notice for `ARBISCAN_API_KEY`
   - Documented that single API key now works for all chains

### Configuration Files
3. **.env.example**
   - Updated comments to reflect V2 single-key model
   - Marked `ARBISCAN_API_KEY` as deprecated
   - Added information about supported chains

4. **DOCKER_SETUP.md**
   - Removed `ARBISCAN_API_KEY` from required keys
   - Added note about V2 multichain support

5. **README.md**
   - Updated prerequisites and API keys section
   - Documented V2 multichain capabilities
   - Removed Arbiscan API key requirement

## Migration Benefits

1. **Simplified Configuration**: Only one API key needed for all chains
2. **Future-Proof**: Ready for Etherscan's V1 deprecation
3. **Expanded Chain Support**: Easy to add support for 60+ chains
4. **Unified Codebase**: Cleaner, more maintainable code

## Backward Compatibility

- The `ARBISCAN_API_KEY` environment variable is still read but no longer used
- Existing `.env` files will continue to work
- No changes required to wallet tracking logic

## Testing

The migration maintains full compatibility with existing functionality:
- ✅ Wallet transaction retrieval
- ✅ Token transfer tracking
- ✅ Internal transaction monitoring
- ✅ Multi-chain support (Ethereum & Arbitrum)

## Next Steps for Users

1. **Obtain an Etherscan API V2 key** at https://etherscan.io/apis
2. **Update your `.env` file** with the new key:
   ```env
   ETHERSCAN_API_KEY=your_v2_api_key_here
   ```
3. **Optional**: Remove the deprecated `ARBISCAN_API_KEY` entry

## Additional Resources

- [Etherscan V2 Migration Guide](https://docs.etherscan.io/v2-migration)
- [Etherscan V2 FAQ](https://docs.etherscan.io/etherscan-v2/support/v2-faq)
- [Supported Chains](https://docs.etherscan.io/etherscan-v2)

## Migration Date

Completed: 2025-11-11
