"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, status
from app.models.user import UserCreate, UserResponse, UserLogin, TokenResponse
from app.services.auth_service import AuthService
from app.dependencies import get_auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user"
)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
) -> UserResponse:
    """
    Register a new user account.

    Args:
        user_data: Email and password

    Returns:
        Created user (without password)

    Raises:
        409: Email already exists
        422: Validation error
    """
    return await auth_service.register_user(user_data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login"
)
async def login(
    credentials: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    """
    Authenticate user and return JWT token.

    Args:
        credentials: Email and password

    Returns:
        JWT token and user info

    Raises:
        401: Invalid credentials
    """
    return await auth_service.login_user(credentials)
