"""User Pydantic models for request/response validation."""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from prisma.models import User  # Prisma database model


class UserCreate(BaseModel):
    """Request model for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class UserResponse(BaseModel):
    """Response model for user data (excludes password)."""

    id: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True  # For Prisma model compatibility


class UserLogin(BaseModel):
    """Request model for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response model for successful login."""

    token: str
    token_type: str = "bearer"
    user: UserResponse


# Export all models
__all__ = [
    "User",  # Prisma database model
    "UserCreate",
    "UserResponse",
    "UserLogin",
    "TokenResponse",
]
