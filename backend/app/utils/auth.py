"""JWT authentication dependency for FastAPI route protection.

Extracts and verifies Supabase-issued JWTs from the Authorization header.
Returns an AuthenticatedUser on success, raises HTTPException on failure.
"""

import logging
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.exceptions import HTTPException
from pydantic import BaseModel

from app.config import Settings

logger = logging.getLogger("app.auth")

_ALGORITHM = "HS256"
_BEARER_PREFIX = "Bearer "


class AuthenticatedUser(BaseModel):
    """Identity of the authenticated user extracted from a verified JWT."""

    id: UUID
    email: str | None = None
    role: str = "authenticated"


def _get_settings(request: Request) -> Settings:
    """Retrieve settings from application state."""
    return request.app.state.settings


def _extract_token(authorization: str | None) -> str:
    """Extract the bearer token from the Authorization header value.

    Raises:
        HTTPException: If header is missing or not a Bearer token.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    if not authorization.startswith(_BEARER_PREFIX):
        raise HTTPException(status_code=401, detail="Invalid authorization scheme")
    return authorization[len(_BEARER_PREFIX):]


def _decode_jwt(token: str, secret: str) -> dict:
    """Decode and verify a JWT using the Supabase JWT secret.

    Raises:
        HTTPException: If the token is expired, malformed, or invalid.
    """
    try:
        return jwt.decode(token, secret, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def _build_user(payload: dict) -> AuthenticatedUser:
    """Construct an AuthenticatedUser from a decoded JWT payload.

    Raises:
        HTTPException: If required claims are missing.
    """
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token missing subject claim")
    return AuthenticatedUser(
        id=UUID(sub),
        email=payload.get("email"),
        role=payload.get("role", "authenticated"),
    )


async def get_current_user(
    request: Request,
    settings: Settings = Depends(_get_settings),
) -> AuthenticatedUser:
    """FastAPI dependency that authenticates the request via JWT.

    Extracts the Bearer token from the Authorization header,
    verifies it against the Supabase JWT secret, and returns
    the authenticated user identity.
    """
    authorization = request.headers.get("Authorization")
    token = _extract_token(authorization)
    payload = _decode_jwt(token, settings.supabase_jwt_secret)
    user = _build_user(payload)
    logger.debug("Authenticated user %s", user.id)
    return user
