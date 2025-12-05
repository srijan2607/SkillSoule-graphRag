"""Unit tests for file validation utilities."""

import pytest
from io import BytesIO
from fastapi import UploadFile, HTTPException
from app.utils.file_validation import (
    validate_file_extension,
    validate_csv_file,
    sanitize_filename,
    get_file_size_mb
)


class TestFileExtensionValidation:
    """Tests for file extension validation."""

    def test_valid_csv_extension(self):
        """Test that .csv extension is accepted."""
        # Should not raise exception
        validate_file_extension("test.csv")
        validate_file_extension("test.CSV")  # Case insensitive

    def test_invalid_extension_raises_400(self):
        """Test that non-CSV extensions are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_extension("test.txt")
        
        assert exc_info.value.status_code == 400
        assert "Only" in exc_info.value.detail
        assert "csv" in exc_info.value.detail.lower()

    def test_multiple_invalid_extensions(self):
        """Test various invalid file types."""
        invalid_files = ["test.exe", "test.pdf", "test.xlsx", "test.json", "test"]
        
        for filename in invalid_files:
            with pytest.raises(HTTPException) as exc_info:
                validate_file_extension(filename)
            assert exc_info.value.status_code == 400


class TestFileSizeValidation:
    """Tests for file size validation."""

    @pytest.mark.asyncio
    async def test_valid_file_size(self):
        """Test that files under 100MB are accepted."""
        # Create 50MB file
        content = b"a" * (50 * 1024 * 1024)
        file = UploadFile(filename="test.csv", file=BytesIO(content))
        
        # Should not raise exception
        size = await file.read()
        await file.seek(0)
        assert len(size) == 50 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_oversized_file_raises_413(self):
        """Test that files over 100MB are rejected."""
        # Create 101MB file
        content = b"a" * (101 * 1024 * 1024)
        file = UploadFile(filename="test.csv", file=BytesIO(content))
        
        with pytest.raises(HTTPException) as exc_info:
            await validate_csv_file(file)
        
        assert exc_info.value.status_code == 413
        assert "100MB" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_exactly_100mb_accepted(self):
        """Test that exactly 100MB file is accepted."""
        # Create exactly 100MB file
        content = b"ID,NAME\n" + b"a" * (100 * 1024 * 1024 - 8)
        file = UploadFile(filename="test.csv", file=BytesIO(content))
        
        # Should not raise exception
        sanitized_name, size_mb = await validate_csv_file(file)
        assert size_mb <= 100


class TestFileSizeMbConversion:
    """Tests for file size MB conversion utility."""

    def test_bytes_to_mb_conversion(self):
        """Test accurate bytes to MB conversion."""
        assert get_file_size_mb(1024 * 1024) == 1.0
        assert get_file_size_mb(50 * 1024 * 1024) == 50.0
        assert get_file_size_mb(512 * 1024) == 0.5

    def test_rounding_to_two_decimals(self):
        """Test that file size is rounded to 2 decimal places."""
        assert get_file_size_mb(1536 * 1024) == 1.5
        assert get_file_size_mb(1234567) == 1.18


class TestFilenameSanitization:
    """Tests for filename sanitization."""

    def test_valid_filename_unchanged(self):
        """Test that valid filenames are not modified."""
        assert sanitize_filename("skills.csv") == "skills.csv"
        assert sanitize_filename("data-2024.csv") == "data-2024.csv"
        assert sanitize_filename("file_name_123.csv") == "file_name_123.csv"

    def test_path_traversal_prevention(self):
        """Test that path traversal attempts are sanitized."""
        assert sanitize_filename("../../../etc/passwd.csv") == "passwd.csv"
        assert sanitize_filename("..\\..\\windows\\system32\\file.csv") == "file.csv"
        assert sanitize_filename("/absolute/path/file.csv") == "file.csv"

    def test_special_characters_replaced(self):
        """Test that special characters are replaced with underscores."""
        assert sanitize_filename("file with spaces.csv") == "file_with_spaces.csv"
        assert sanitize_filename("file@#$%.csv") == "file____.csv"
        assert sanitize_filename("file(1).csv") == "file_1_.csv"

    def test_preserve_extension(self):
        """Test that file extensions are preserved."""
        assert sanitize_filename("malicious!script.csv").endswith(".csv")
        assert sanitize_filename("bad@file.CSV").endswith(".CSV")


class TestComprehensiveCSVValidation:
    """Integration tests for complete CSV file validation."""

    @pytest.mark.asyncio
    async def test_valid_csv_file_success(self):
        """Test successful validation of a valid CSV file."""
        content = b"ID,NAME,DESCRIPTION\n1,Python,Programming language\n2,Java,OOP language"
        file = UploadFile(filename="skills.csv", file=BytesIO(content))
        
        sanitized_name, size_mb = await validate_csv_file(file)
        
        assert sanitized_name == "skills.csv"
        assert size_mb > 0
        assert size_mb < 1  # Small file

    @pytest.mark.asyncio
    async def test_invalid_extension_rejected(self):
        """Test that files with wrong extension are rejected."""
        content = b"ID,NAME\n1,Python"
        file = UploadFile(filename="malicious.exe", file=BytesIO(content))
        
        with pytest.raises(HTTPException) as exc_info:
            await validate_csv_file(file)
        
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_unsafe_filename_sanitized(self):
        """Test that unsafe filenames are sanitized."""
        content = b"ID,NAME\n1,Python"
        file = UploadFile(filename="../../../etc/passwd.csv", file=BytesIO(content))
        
        sanitized_name, size_mb = await validate_csv_file(file)
        
        assert sanitized_name == "passwd.csv"
        assert "/" not in sanitized_name
        assert "\\" not in sanitized_name

    @pytest.mark.asyncio
    async def test_file_pointer_reset_after_validation(self):
        """Test that file pointer is reset to beginning after validation."""
        content = b"ID,NAME\n1,Python\n2,Java"
        file = UploadFile(filename="test.csv", file=BytesIO(content))
        
        await validate_csv_file(file)
        
        # File pointer should be at beginning
        data = await file.read()
        assert data == content
