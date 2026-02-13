"""
Authentication endpoints: register, login, API key management.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends

from src.api.auth.security import (
    hash_password, verify_password, create_jwt_token,
    generate_api_key, get_current_user,
)
from src.api.models.schemas import (
    UserRegister, UserLogin, TokenResponse,
    APIKeyCreate, APIKeyResponse, APIKeyInfo,
)
from src.database import mongodb as db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse)
async def register(body: UserRegister):
    """Register a new user account."""
    existing = await db.get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    password_hash = hash_password(body.password)
    user_id = await db.create_user(body.email, password_hash, body.name)

    token = create_jwt_token(user_id, body.email)
    logger.info(f"New user registered: {body.email}")

    return TokenResponse(
        access_token=token,
        user_id=user_id,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin):
    """Login and get a JWT access token."""
    user = await db.get_user_by_email(body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_id = str(user["_id"])
    token = create_jwt_token(user_id, body.email)

    return TokenResponse(
        access_token=token,
        user_id=user_id,
    )


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(body: APIKeyCreate, user=Depends(get_current_user)):
    """Generate a new API key for programmatic access."""
    # Limit API keys per user
    existing_keys = user.get("api_keys", [])
    if len(existing_keys) >= 10:
        raise HTTPException(status_code=400, detail="Maximum 10 API keys per account")

    key_id, raw_key, key_hash = generate_api_key()

    key_data = {
        "key_id": key_id,
        "key_hash": key_hash,
        "name": body.name,
        "permissions": body.permissions,
        "created_at": datetime.utcnow(),
        "last_used": None,
    }

    await db.add_api_key(str(user["_id"]), key_data)
    logger.info(f"API key created: {key_id} for user {user['email']}")

    return APIKeyResponse(
        key_id=key_id,
        api_key=raw_key,  # Only returned once
        name=body.name,
        permissions=body.permissions,
        created_at=key_data["created_at"],
    )


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str, user=Depends(get_current_user)):
    """Revoke an API key."""
    user_keys = user.get("api_keys", [])
    if not any(k["key_id"] == key_id for k in user_keys):
        raise HTTPException(status_code=404, detail="API key not found")

    await db.remove_api_key(str(user["_id"]), key_id)
    logger.info(f"API key revoked: {key_id}")

    return {"status": "revoked", "key_id": key_id}
