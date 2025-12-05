"""User database operations."""

from typing import Optional
from prisma import Prisma
from prisma.models import User


class UserRepository:
    """Repository for User model operations."""

    def __init__(self, db: Prisma):
        self.db = db

    async def find_by_email(self, email: str) -> Optional[User]:
        """
        Find user by email address.

        Args:
            email: User email

        Returns:
            User if found, None otherwise
        """
        return await self.db.user.find_unique(where={"email": email})

    async def create(self, user_data: dict) -> User:
        """
        Create new user.

        Args:
            user_data: Dictionary with user fields

        Returns:
            Created user

        Raises:
            Exception: If database operation fails
        """
        return await self.db.user.create(data=user_data)
