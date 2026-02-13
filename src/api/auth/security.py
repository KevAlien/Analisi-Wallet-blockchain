"""
Authentication and authorization for the SaaS API.
Supports JWT tokens (human users) and API keys (agents/bots).
"""
import os
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader

from src.database import mongodb as db
from src.api.models.schemas import Tier, UsageLimits

logger = logging.getLogger(__name__)

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production-please")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_jwt_token(user_id: str, email: str) -> str:
    """Create a JWT access token."""
    payload = {
        "sub": user_id,
        "email": email,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key. Returns (key_id, raw_key, key_hash)."""
    key_id = f"wt_{secrets.token_hex(8)}"
    raw_key = f"wt_sk_{secrets.token_hex(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return key_id, raw_key, key_hash


def hash_api_key(raw_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
) -> Dict[str, Any]:
    """
    Authenticate the current user via JWT bearer token or API key.
    Returns the user document from MongoDB.
    """
    user = None

    # Try JWT first
    if credentials and credentials.credentials:
        payload = decode_jwt_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id:
            user = await db.get_user_by_id(user_id)

    # Try API key
    if not user and api_key:
        key_hash = hash_api_key(api_key)
        user = await db.get_user_by_api_key_hash(key_hash)
        if user:
            # Find and update last_used for this key
            for ak in user.get("api_keys", []):
                if ak["key_hash"] == key_hash:
                    await db.update_api_key_last_used(
                        str(user["_id"]), ak["key_id"]
                    )
                    break

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Increment API call counter
    await db.increment_usage(str(user["_id"]), "api_calls_today")

    return user


async def check_rate_limit(user: Dict[str, Any]):
    """Check if user has exceeded their rate limit."""
    tier = Tier(user.get("tier", "free"))
    limits = UsageLimits.for_tier(tier)

    usage = user.get("usage", {})
    api_calls = usage.get("api_calls_today", 0)

    # Simple daily rate limiting (per-minute would use Redis in production)
    daily_limit = limits.api_calls_per_minute * 60 * 24
    if api_calls > daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for {tier.value} tier. "
                   f"Upgrade your plan for higher limits.",
        )


async def check_tier_permission(user: Dict[str, Any], required_tier: Tier):
    """Check if user's tier meets the required level."""
    tier_order = {Tier.FREE: 0, Tier.PRO: 1, Tier.ENTERPRISE: 2}
    user_tier = Tier(user.get("tier", "free"))

    if tier_order[user_tier] < tier_order[required_tier]:
        raise HTTPException(
            status_code=403,
            detail=f"This feature requires {required_tier.value} tier or higher. "
                   f"Current tier: {user_tier.value}",
        )
