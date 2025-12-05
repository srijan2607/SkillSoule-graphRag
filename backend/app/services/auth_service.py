"""Authentication business logic."""

from fastapi import HTTPException, status
from app.models.user import UserCreate, UserResponse, UserLogin, TokenResponse
from app.repositories.user_repository import UserRepository
from app.utils.password import hash_password, verify_password
from app.utils.jwt import create_access_token


class AuthService:
    """Service for user authentication operations."""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register_user(self, user_data: UserCreate) -> UserResponse:
        """
        Register new user account.

        Args:
            user_data: User registration data

        Returns:
            Created user response

        Raises:
            HTTPException: If email already exists
        """
        # Check for duplicate email
        existing_user = await self.user_repo.find_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists"
            )

        # Hash password
        password_hash = hash_password(user_data.password)

        # Create user
        user = await self.user_repo.create({
            "email": user_data.email,
            "password_hash": password_hash
        })

        return UserResponse.model_validate(user)

    async def login_user(self, credentials: UserLogin) -> TokenResponse:
        """
        Authenticate user and generate JWT token.

        Args:
            credentials: Email and password

        Returns:
            Token and user info

        Raises:
            HTTPException: 401 if credentials invalid
        """
        # Find user by email
        user = await self.user_repo.find_by_email(credentials.email)

        # Constant-time comparison to prevent email enumeration
        if not user or not verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Generate JWT token
        token = create_access_token(user.id, user.email)

        # Return token and user info
        return TokenResponse(
            token=token,
            user=UserResponse.model_validate(user)
        )
