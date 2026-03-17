"""
Nutri JWT Authentication Module

Server-side JWT creation and verification.
The secret NEVER leaves the backend.
"""

import os
import uuid
import time
import logging
import jwt  # PyJWT

from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────────
JWT_SECRET = os.environ.get("JWT_SECRET", "nutri-dev-secret-do-not-use-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_SECONDS = 86400  # 24 hours

DEV_MODE = os.environ.get("NUTRI_DEV_MODE", "true").lower() == "true"

if JWT_SECRET == "nutri-dev-secret-do-not-use-in-prod":
    logger.warning("⚠️  AUTH: Using default dev JWT secret. Set JWT_SECRET env var for production!")


# ─── Token Creation (Server-Side Only) ──────────────────────────
def create_dev_token(user_id: str | None = None) -> dict:
    """
    Signs a JWT with the server secret.
    Called by POST /api/dev-login — never exposed to the client.
    """
    if not user_id:
        user_id = f"dev_{uuid.uuid4().hex[:12]}"

    now = int(time.time())
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + JWT_EXPIRY_SECONDS,
        "iss": "nutri-backend",
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    logger.info(f"[AUTH] Dev token issued for user_id={user_id}")

    return {
        "token": token,
        "user_id": user_id,
        "expires_in": JWT_EXPIRY_SECONDS,
    }


# ─── Token Verification ─────────────────────────────────────────
def decode_token(token: str) -> dict:
    """
    Decodes and validates a JWT. Returns the payload.
    Raises HTTPException on failure.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


# ─── Request-Level Auth ──────────────────────────────────────────
def get_authenticated_user(request: Request) -> str:
    """
    Extracts user_id from JWT.

    Priority:
      1. Authorization: Bearer <token> header
      2. ?token=<token> query param (for EventSource/SSE)

    Returns the user_id (sub claim).
    """
    token = None

    # 1. Header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]

    # 2. Query param fallback (SSE)
    if not token:
        token = request.query_params.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    payload = decode_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing 'sub' claim")

    return user_id
