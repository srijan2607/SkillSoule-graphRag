"""Authentication middleware for protected endpoints."""

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from app.utils.jwt import verify_access_token
from app.exceptions import AuthenticationError

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract and verify JWT token from Authorization header.

    Args:
        credentials: HTTP Bearer credentials from header

    Returns:
        User ID from verified token

    Raises:
        AuthenticationError: If token invalid or expired
    """
    token = credentials.credentials

    try:
        user_id = verify_access_token(token)
        return user_id

    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token expired")

    except jwt.InvalidTokenError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")

    except Exception as e:
        raise AuthenticationError(f"Authentication failed: {str(e)}")


# Alias for clarity in other modules
get_current_user_id = get_current_user
