"""Query history database operations."""

from typing import Optional, List
from datetime import datetime, timedelta, UTC
from prisma import Prisma
from prisma.models import QueryHistory


class QueryHistoryRepository:
    """Repository for QueryHistory model operations."""

    def __init__(self, db: Prisma):
        self.db = db

    async def create_query_history(
        self,
        user_id: str,
        query_text: str,
        response_text: str,
        metadata: str,
        session_id: Optional[str] = None
    ) -> QueryHistory:
        """
        Log a query and response to database.

        Args:
            user_id: ID of user who made the query
            query_text: Original query text
            response_text: Generated response
            metadata: JSON string with additional metadata (processing time, sources, etc.)
            session_id: Optional session ID for conversation grouping

        Returns:
            Created QueryHistory record

        Raises:
            Exception: If database operation fails
        """
        return await self.db.queryhistory.create(
            data={
                "user_id": user_id,
                "session_id": session_id,
                "query_text": query_text,
                "response_text": response_text,
                "metadata": metadata
            }
        )

    async def find_by_user(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[QueryHistory]:
        """
        Retrieve query history for a user.

        Args:
            user_id: ID of user
            limit: Maximum number of records to return

        Returns:
            List of QueryHistory records, ordered by most recent first
        """
        return await self.db.queryhistory.find_many(
            where={"user_id": user_id},
            order={"created_at": "desc"},
            take=limit
        )

    async def find_by_id(self, query_id: str) -> Optional[QueryHistory]:
        """
        Find query history record by ID.

        Args:
            query_id: Query history record ID

        Returns:
            QueryHistory if found, None otherwise
        """
        return await self.db.queryhistory.find_unique(
            where={"id": query_id}
        )

    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 10,
        max_age_hours: int = 24
    ) -> List[QueryHistory]:
        """
        Retrieve conversation history for a session with age filter.

        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return (default: 10)
            max_age_hours: Maximum age of conversation in hours (default: 24)

        Returns:
            List of QueryHistory records for the session within the age limit,
            ordered chronologically (oldest first). Empty list if session expired.
        """
        cutoff_time = datetime.now(UTC) - timedelta(hours=max_age_hours)

        return await self.db.queryhistory.find_many(
            where={
                "session_id": session_id,
                "created_at": {"gte": cutoff_time}  # Filter by age
            },
            order={"created_at": "asc"},  # Oldest first for conversation flow
            take=limit
        )

    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        Delete query history records older than specified days.

        This method should be called periodically to prevent database bloat
        from accumulating old conversation history.

        Args:
            days: Number of days to keep (default: 30)

        Returns:
            Number of records deleted

        Example:
            >>> deleted = await repo.cleanup_old_sessions(days=30)
            >>> print(f"Cleaned up {deleted} old records")
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        result = await self.db.queryhistory.delete_many(
            where={"created_at": {"lt": cutoff_date}}
        )

        return result
