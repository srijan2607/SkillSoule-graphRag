"""Temporary file storage for CSV previews.

⚠️ IMPORTANT: This is an MVP implementation using in-memory storage.
For production deployment, replace with Redis for:
- Persistence across server restarts
- Distributed support for load balancing
- Better memory management
- Automatic TTL-based cleanup

See Story 2.3 Dev Notes for Redis migration example.
"""
import hashlib
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta

# Configure logger
logger = logging.getLogger(__name__)

# Simple in-memory cache for MVP (replace with Redis for production)
# Structure: {file_hash: {content, file_type, filename, file_size_mb, expires_at}}
_file_cache: Dict[str, Dict] = {}


def store_temp_file(
    content: bytes,
    file_type: str,
    filename: str,
    ttl_hours: int = 1
) -> str:
    """
    Store file content temporarily with TTL.

    This function stores uploaded CSV files temporarily while waiting
    for user confirmation. Files are identified by SHA-256 hash and
    automatically expire after TTL.

    Args:
        content: File content as bytes
        file_type: "skills" or "jobs"
        filename: Original filename (for ingestion job creation)
        ttl_hours: Time to live in hours (default: 1)

    Returns:
        File hash (SHA-256) as identifier

    Example:
        >>> content = b"ID,NAME\\n1,Python"
        >>> file_hash = store_temp_file(content, "skills", "skills.csv")
        >>> print(file_hash)  # '3a5f...' (64-char SHA-256 hash)
    """
    # Generate SHA-256 hash as unique identifier
    file_hash = hashlib.sha256(content).hexdigest()

    # Calculate file size
    file_size_mb = len(content) / (1024 * 1024)

    # Calculate expiry time
    expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)

    # Store in cache with expiry and metadata
    _file_cache[file_hash] = {
        "content": content,
        "file_type": file_type,
        "filename": filename,  # Preserve original filename for job creation
        "file_size_mb": file_size_mb,  # For ingestion job metadata
        "expires_at": expires_at
    }

    logger.debug(
        f"Stored temporary file: hash={file_hash[:16]}..., "
        f"type={file_type}, filename={filename}, "
        f"size={file_size_mb:.2f}MB, ttl={ttl_hours}h, "
        f"expires_at={expires_at.isoformat()}"
    )
    logger.info(
        f"Temporary file cached. Type: {file_type}, "
        f"Size: {file_size_mb:.2f}MB, Cache size: {len(_file_cache)} files"
    )

    return file_hash


def retrieve_temp_file(file_hash: str) -> Optional[Dict]:
    """
    Retrieve temporary file content and metadata by hash.

    Args:
        file_hash: SHA-256 hash identifier

    Returns:
        Dict with file metadata if found and not expired:
        {
            "content": bytes,
            "file_type": str,
            "filename": str,
            "file_size_mb": float
        }
        Returns None if not found or expired.

    Example:
        >>> file_data = retrieve_temp_file(file_hash)
        >>> if file_data:
        ...     content = file_data["content"]
        ...     filename = file_data["filename"]
    """
    if file_hash not in _file_cache:
        logger.warning(f"File not found in cache: hash={file_hash[:16]}...")
        return None

    cached_file = _file_cache[file_hash]

    # Check if expired
    if datetime.utcnow() > cached_file["expires_at"]:
        logger.warning(
            f"File expired in cache: hash={file_hash[:16]}..., "
            f"expired_at={cached_file['expires_at'].isoformat()}"
        )
        del _file_cache[file_hash]
        return None

    logger.debug(f"Retrieved temporary file: hash={file_hash[:16]}...")

    # Return metadata without expires_at (not needed by caller)
    return {
        "content": cached_file["content"],
        "file_type": cached_file["file_type"],
        "filename": cached_file["filename"],
        "file_size_mb": cached_file["file_size_mb"]
    }


def delete_temp_file(file_hash: str) -> bool:
    """
    Delete temporary file from cache.

    This should be called after successful ingestion confirmation
    or when user cancels the upload.

    Args:
        file_hash: SHA-256 hash identifier

    Returns:
        True if deleted, False if not found

    Example:
        >>> if delete_temp_file(file_hash):
        ...     print("File cleaned up successfully")
    """
    if file_hash in _file_cache:
        logger.info(f"Deleting temporary file: hash={file_hash[:16]}...")
        del _file_cache[file_hash]
        return True

    logger.debug(f"File not found for deletion: hash={file_hash[:16]}...")
    return False


def cleanup_expired_files() -> int:
    """
    Remove all expired files from cache.

    This function is called by the background scheduler (APScheduler)
    every 15 minutes to prevent memory leaks from expired files.

    Returns:
        Number of files cleaned up

    Example:
        >>> cleaned = cleanup_expired_files()
        >>> print(f"Cleaned up {cleaned} expired files")
    """
    now = datetime.utcnow()
    expired_hashes = [
        file_hash
        for file_hash, data in _file_cache.items()
        if now > data["expires_at"]
    ]

    for file_hash in expired_hashes:
        logger.debug(f"Cleaning up expired file: hash={file_hash[:16]}...")
        del _file_cache[file_hash]

    if len(expired_hashes) > 0:
        logger.info(
            f"Cleanup complete. Removed {len(expired_hashes)} expired files. "
            f"Cache size: {len(_file_cache)} files"
        )

    return len(expired_hashes)


def get_cache_stats() -> Dict:
    """
    Get cache statistics for monitoring.

    Returns:
        Dict with cache statistics:
        {
            "total_files": int,
            "total_size_mb": float,
            "oldest_expires_at": datetime,
            "newest_expires_at": datetime
        }

    Example:
        >>> stats = get_cache_stats()
        >>> print(f"Cache contains {stats['total_files']} files")
    """
    if not _file_cache:
        return {
            "total_files": 0,
            "total_size_mb": 0.0,
            "oldest_expires_at": None,
            "newest_expires_at": None
        }

    total_size_mb = sum(data["file_size_mb"] for data in _file_cache.values())
    expires_times = [data["expires_at"] for data in _file_cache.values()]

    return {
        "total_files": len(_file_cache),
        "total_size_mb": round(total_size_mb, 2),
        "oldest_expires_at": min(expires_times),
        "newest_expires_at": max(expires_times)
    }
