"""
MongoDB async connection and database operations.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId

logger = logging.getLogger(__name__)

# Global database instance
_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect_db() -> AsyncIOMotorDatabase:
    """Connect to MongoDB and return the database instance."""
    global _client, _db

    mongo_uri = os.getenv("MONGODB_URI", "mongodb://mongodb:27017")
    db_name = os.getenv("DATABASE_NAME", "whale_tracker")

    _client = AsyncIOMotorClient(mongo_uri)
    _db = _client[db_name]

    # Create indexes
    await _create_indexes()

    logger.info(f"Connected to MongoDB: {db_name}")
    return _db


async def close_db():
    """Close MongoDB connection."""
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed")


async def get_db() -> AsyncIOMotorDatabase:
    """Get the database instance."""
    if _db is None:
        return await connect_db()
    return _db


async def _create_indexes():
    """Create database indexes for performance."""
    db = _db

    # Users indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("api_keys.key_hash")

    # Signals indexes
    await db.signals.create_index([("user_id", 1), ("created_at", -1)])
    await db.signals.create_index([("signal_type", 1), ("created_at", -1)])
    await db.signals.create_index([("chain", 1), ("wallet_address", 1)])
    await db.signals.create_index("expires_at", expireAfterSeconds=0)

    # Wallets indexes
    await db.tracked_wallets.create_index(
        [("user_id", 1), ("address", 1), ("chain", 1)], unique=True
    )

    # Trades indexes
    await db.trades.create_index([("user_id", 1), ("created_at", -1)])
    await db.trades.create_index([("user_id", 1), ("status", 1)])

    logger.info("Database indexes created")


# --- User Operations ---

async def create_user(email: str, password_hash: str, name: Optional[str] = None) -> str:
    """Create a new user. Returns user_id."""
    db = await get_db()
    result = await db.users.insert_one({
        "email": email,
        "password_hash": password_hash,
        "name": name,
        "tier": "free",
        "api_keys": [],
        "settings": {
            "default_chain": "ethereum",
            "notification_channels": [],
            "risk_per_trade_pct": 1.0,
        },
        "usage": {
            "signals_today": 0,
            "api_calls_today": 0,
            "last_reset": datetime.utcnow(),
        },
        "created_at": datetime.utcnow(),
    })
    return str(result.inserted_id)


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email."""
    db = await get_db()
    return await db.users.find_one({"email": email})


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    db = await get_db()
    return await db.users.find_one({"_id": ObjectId(user_id)})


async def get_user_by_api_key_hash(key_hash: str) -> Optional[Dict[str, Any]]:
    """Get user by API key hash."""
    db = await get_db()
    return await db.users.find_one({"api_keys.key_hash": key_hash})


async def add_api_key(user_id: str, key_data: Dict[str, Any]):
    """Add an API key to user."""
    db = await get_db()
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$push": {"api_keys": key_data}},
    )


async def remove_api_key(user_id: str, key_id: str):
    """Remove an API key from user."""
    db = await get_db()
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$pull": {"api_keys": {"key_id": key_id}}},
    )


async def update_api_key_last_used(user_id: str, key_id: str):
    """Update API key last_used timestamp."""
    db = await get_db()
    await db.users.update_one(
        {"_id": ObjectId(user_id), "api_keys.key_id": key_id},
        {"$set": {"api_keys.$.last_used": datetime.utcnow()}},
    )


async def increment_usage(user_id: str, field: str, amount: int = 1):
    """Increment a usage counter, resetting if past midnight."""
    db = await get_db()
    user = await get_user_by_id(user_id)
    if not user:
        return

    last_reset = user.get("usage", {}).get("last_reset", datetime.utcnow())
    now = datetime.utcnow()

    if now.date() > last_reset.date():
        # Reset daily counters
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "usage.signals_today": 0,
                    "usage.api_calls_today": 0,
                    "usage.last_reset": now,
                }
            },
        )

    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$inc": {f"usage.{field}": amount}},
    )


# --- Wallet Operations ---

async def add_tracked_wallet(
    user_id: str, address: str, chain: str,
    label: Optional[str] = None, alert_threshold_eth: float = 50.0
) -> str:
    """Add a wallet to track for a user."""
    db = await get_db()
    result = await db.tracked_wallets.insert_one({
        "user_id": ObjectId(user_id),
        "address": address.lower(),
        "chain": chain,
        "label": label,
        "alert_threshold_eth": alert_threshold_eth,
        "added_at": datetime.utcnow(),
        "total_signals": 0,
    })
    return str(result.inserted_id)


async def get_tracked_wallets(user_id: str) -> List[Dict[str, Any]]:
    """Get all tracked wallets for a user."""
    db = await get_db()
    cursor = db.tracked_wallets.find({"user_id": ObjectId(user_id)})
    return await cursor.to_list(length=1000)


async def remove_tracked_wallet(user_id: str, address: str):
    """Remove a tracked wallet."""
    db = await get_db()
    await db.tracked_wallets.delete_one({
        "user_id": ObjectId(user_id),
        "address": address.lower(),
    })


async def count_tracked_wallets(user_id: str) -> int:
    """Count tracked wallets for a user."""
    db = await get_db()
    return await db.tracked_wallets.count_documents({"user_id": ObjectId(user_id)})


# --- Signal Operations ---

async def store_signal(user_id: str, signal_data: Dict[str, Any]) -> str:
    """Store a signal in the database."""
    db = await get_db()
    signal_data["user_id"] = ObjectId(user_id)
    signal_data["created_at"] = datetime.utcnow()

    # Set expiry based on tier (will be cleaned up by MongoDB TTL index)
    if "expires_at" not in signal_data:
        signal_data["expires_at"] = datetime.utcnow() + timedelta(days=90)

    result = await db.signals.insert_one(signal_data)
    return str(result.inserted_id)


async def get_signals(
    user_id: str,
    signal_type: Optional[str] = None,
    chain: Optional[str] = None,
    min_confidence: Optional[float] = None,
    min_value_eth: Optional[float] = None,
    since: Optional[datetime] = None,
    wallet_address: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[List[Dict[str, Any]], int]:
    """Get signals with filtering. Returns (signals, total_count)."""
    db = await get_db()

    query: Dict[str, Any] = {"user_id": ObjectId(user_id)}
    if signal_type:
        query["signal_type"] = signal_type
    if chain:
        query["chain"] = chain
    if min_confidence is not None:
        query["confidence"] = {"$gte": min_confidence}
    if min_value_eth is not None:
        query["value_eth"] = {"$gte": min_value_eth}
    if since:
        query["created_at"] = {"$gte": since}
    if wallet_address:
        query["wallet_address"] = wallet_address.lower()

    total = await db.signals.count_documents(query)
    skip = (page - 1) * page_size

    cursor = db.signals.find(query).sort("created_at", -1).skip(skip).limit(page_size)
    signals = await cursor.to_list(length=page_size)

    return signals, total


async def get_signal_by_id(signal_id: str) -> Optional[Dict[str, Any]]:
    """Get a signal by ID."""
    db = await get_db()
    return await db.signals.find_one({"_id": ObjectId(signal_id)})


# --- Trade Operations ---

async def store_trade(user_id: str, trade_data: Dict[str, Any]) -> str:
    """Store a trade record."""
    db = await get_db()
    trade_data["user_id"] = ObjectId(user_id)
    trade_data["created_at"] = datetime.utcnow()
    result = await db.trades.insert_one(trade_data)
    return str(result.inserted_id)


async def get_trades(
    user_id: str, status: Optional[str] = None,
    page: int = 1, page_size: int = 50
) -> tuple[List[Dict[str, Any]], int]:
    """Get trades for a user."""
    db = await get_db()

    query: Dict[str, Any] = {"user_id": ObjectId(user_id)}
    if status:
        query["status"] = status

    total = await db.trades.count_documents(query)
    skip = (page - 1) * page_size

    cursor = db.trades.find(query).sort("created_at", -1).skip(skip).limit(page_size)
    trades = await cursor.to_list(length=page_size)

    return trades, total
