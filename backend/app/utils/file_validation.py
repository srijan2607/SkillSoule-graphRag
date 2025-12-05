"""File validation utilities for ingestion endpoints."""

import os
import re
import filetype
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException, status

from app.config import settings


# Configuration - Use settings from config
MAX_FILE_SIZE_MB = settings.MAX_FILE_SIZE_MB
ALLOWED_EXTENSIONS = {".csv"}
ALLOWED_MIME_TYPES = {"text/csv", "text/plain", "application/csv"}
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename (basename only, no directory components)
    """
    # Normalize path separators (handle both Unix and Windows)
    # Replace backslashes with forward slashes
    normalized = filename.replace('\\', '/')

    # Get basename to remove any directory components
    basename = os.path.basename(normalized)

    # Remove any remaining potentially dangerous characters
    # Keep only alphanumeric, dots, hyphens, and underscores
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', basename)

    return sanitized


def validate_file_extension(filename: str) -> None:
    """
    Validate that file has an allowed extension.

    Args:
        filename: Filename to validate

    Raises:
        HTTPException: 400 if extension is not allowed
    """
    _, ext = os.path.splitext(filename.lower())

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Only {', '.join(ALLOWED_EXTENSIONS)} files are allowed"
        )


async def validate_file_size(file: UploadFile) -> int:
    """
    Validate that file size is within allowed limits.

    Args:
        file: UploadFile to validate

    Returns:
        File size in bytes

    Raises:
        HTTPException: 413 if file is too large
    """
    # Read file in chunks to get size without loading entire file into memory
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks

    # Reset file pointer to beginning
    await file.seek(0)

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        file_size += len(chunk)

        # Check if size exceeds limit during reading
        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE_MB}MB"
            )

    # Reset file pointer to beginning for subsequent reads
    await file.seek(0)

    return file_size


def get_file_size_mb(file_size_bytes: int) -> float:
    """
    Convert file size from bytes to megabytes.

    Args:
        file_size_bytes: File size in bytes

    Returns:
        File size in megabytes (rounded to 2 decimal places, minimum 0.01 for non-empty files)
    """
    size_mb = round(file_size_bytes / (1024 * 1024), 2)
    # Ensure non-empty files report at least 0.01 MB
    if file_size_bytes > 0 and size_mb == 0.0:
        return 0.01
    return size_mb


async def validate_mime_type(file: UploadFile) -> None:
    """
    Validate file MIME type using filetype library.

    Args:
        file: UploadFile to validate

    Raises:
        HTTPException: 400 if MIME type is not allowed
    """
    # Read first 8192 bytes to detect file type
    await file.seek(0)
    file_header = await file.read(8192)
    await file.seek(0)

    # Detect file type
    kind = filetype.guess(file_header)

    # CSV files are plain text, so filetype might return None
    # or detect them as text. We need to do additional validation.
    # For CSV specifically, we'll accept:
    # 1. Files that filetype can't identify (likely plain text/CSV)
    # 2. Files identified as text/plain
    if kind is not None:
        mime_type = kind.mime
        if mime_type not in ALLOWED_MIME_TYPES:
            # Additional check: if it's detected as something else, reject
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Detected MIME type: {mime_type}. Only CSV files are allowed."
            )

    # If filetype returns None, it's likely a text file (CSV)
    # We'll allow it since extension validation already passed


async def validate_csv_file(file: UploadFile) -> Tuple[str, float]:
    """
    Comprehensive validation for uploaded CSV files.

    Validates:
    - File extension is .csv
    - File MIME type is CSV
    - File size is within limits
    - Filename is sanitized

    Args:
        file: UploadFile to validate

    Returns:
        Tuple of (sanitized_filename, file_size_in_mb)

    Raises:
        HTTPException: 400 for invalid file type, 413 for file too large
    """
    # Validate extension
    validate_file_extension(file.filename)

    # Validate MIME type (checks actual file content)
    await validate_mime_type(file)

    # Sanitize filename
    sanitized_filename = sanitize_filename(file.filename)

    # Validate size
    file_size_bytes = await validate_file_size(file)
    file_size_mb = get_file_size_mb(file_size_bytes)

    return sanitized_filename, file_size_mb
