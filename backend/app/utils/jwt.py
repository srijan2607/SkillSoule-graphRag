"""JWT token utilities for authentication."""

import jwt
from datetime import datetime, timedelta
from app.config import settings


def create_access_token(user_id: str, email: str) -> str:
    """
    Generate JWT access token for authenticated user.

    Args:
        user_id: Unique user identifier
        email: User email address

    Returns:
        Encoded JWT token string
    """
    payload = {
        "sub": user_id,  # Subject (user ID)
        "email": email,
        "iat": datetime.utcnow(),  # Issued at
        "exp": datetime.utcnow() + timedelta(
            hours=settings.JWT_EXPIRATION_HOURS
        )
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    return token


def verify_access_token(token: str) -> str:
    """
    Verify JWT token and extract user ID.

    Args:
        token: JWT token string

    Returns:
        User ID from token payload

    Raises:
        jwt.ExpiredSignatureError: Token expired
        jwt.InvalidTokenError: Token invalid or missing user ID
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")

        if not user_id:
            raise jwt.InvalidTokenError("Missing user ID in token")

        return user_id

    except jwt.ExpiredSignatureError:
        raise
    except jwt.InvalidTokenError:
        raise


def verify_jwt_token(token: str) -> dict:
    """
    Verify JWT token and return full payload.

    Alias function for backward compatibility with dependencies.py.

    Args:
        token: JWT token string

    Returns:
        Full token payload as dictionary

    Raises:
        jwt.ExpiredSignatureError: Token expired
        jwt.InvalidTokenError: Token invalid
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM]
    )

    # Add user_id as alias for 'sub' for easier access
    if "sub" in payload:
        payload["user_id"] = payload["sub"]

    return payload
