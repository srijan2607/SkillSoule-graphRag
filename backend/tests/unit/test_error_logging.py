"""
Unit tests for error logging and CSV export functionality (Story 2.6).

Tests cover:
- CSV export formatting
- Error summary message formatting
- Error message sanitization
- Partial success response formatting
"""

import pytest
from unittest.mock import Mock
from app.utils.csv_export import errors_to_csv, format_error_summary


def create_mock_error(row_number: int, error_message: str, raw_data: str):
    """Create a mock IngestionError for testing."""
    error = Mock()
    error.row_number = row_number
    error.error_message = error_message
    error.raw_data = raw_data
    return error


@pytest.mark.unit
def test_errors_to_csv_basic():
    """Test CSV export with basic error data."""
    errors = [
        create_mock_error(
            row_number=15,
            error_message='Missing required field: NAME',
            raw_data='{"ID": "123"}'
        ),
        create_mock_error(
            row_number=42,
            error_message='Invalid data type: LEVEL must be integer',
            raw_data='{"ID": "456", "NAME": "Python", "LEVEL": "abc"}'
        )
    ]

    csv_content = errors_to_csv(errors)
    csv_text = csv_content.decode('utf-8')

    # Verify header (with quotes due to QUOTE_ALL)
    assert 'row_number' in csv_text
    assert 'error_message' in csv_text
    assert 'raw_data' in csv_text

    # Verify row numbers
    assert '15' in csv_text
    assert '42' in csv_text

    # Verify error messages
    assert 'Missing required field: NAME' in csv_text
    assert 'Invalid data type: LEVEL must be integer' in csv_text

    # Verify raw data is included (quotes are escaped in CSV)
    assert 'ID' in csv_text
    assert '123' in csv_text
    assert 'Python' in csv_text
    assert 'LEVEL' in csv_text


@pytest.mark.unit
def test_errors_to_csv_with_special_characters():
    """Test CSV export handles special characters correctly."""
    errors = [
        create_mock_error(
            row_number=5,
            error_message='Error with "quotes" and commas, semicolons;',
            raw_data='{"field": "value with, comma and \\"quotes\\""}'
        )
    ]

    csv_content = errors_to_csv(errors)
    csv_text = csv_content.decode('utf-8')

    # CSV should handle quotes and commas properly
    assert '5' in csv_text
    assert 'quotes' in csv_text
    assert 'comma' in csv_text


@pytest.mark.unit
def test_errors_to_csv_empty_list():
    """Test CSV export with empty error list."""
    errors = []

    csv_content = errors_to_csv(errors)
    csv_text = csv_content.decode('utf-8')

    # Should still have header (with quotes due to QUOTE_ALL)
    assert 'row_number' in csv_text
    assert 'error_message' in csv_text
    assert 'raw_data' in csv_text

    # Should only have one line (header)
    lines = csv_text.strip().split('\n')
    assert len(lines) == 1


@pytest.mark.unit
def test_errors_to_csv_multiple_errors():
    """Test CSV export with multiple errors."""
    errors = [
        create_mock_error(i, f"Error {i}", f'{{"row": "{i}"}}')
        for i in range(1, 101)  # 100 errors
    ]

    csv_content = errors_to_csv(errors)
    csv_text = csv_content.decode('utf-8')

    # Should have header + 100 data rows
    lines = csv_text.strip().split('\n')
    assert len(lines) == 101  # Header + 100 errors


@pytest.mark.unit
def test_format_error_summary_all_success():
    """Test error summary with no failures."""
    message = format_error_summary(
        total_records=40523,
        processed_records=40523,
        failed_records=0
    )

    assert "All 40,523 records ingested successfully." in message
    assert "failed" not in message.lower()
    assert "Download" not in message


@pytest.mark.unit
def test_format_error_summary_partial_success():
    """Test error summary with some failures (AC: 7)."""
    message = format_error_summary(
        total_records=40523,
        processed_records=40518,
        failed_records=5
    )

    # Should match expected format from story
    assert "40,518 / 40,523" in message
    assert "5 failed" in message
    assert "Download error log to review failures" in message


@pytest.mark.unit
def test_format_error_summary_many_failures():
    """Test error summary with many failures."""
    message = format_error_summary(
        total_records=1000,
        processed_records=750,
        failed_records=250
    )

    assert "750 / 1,000" in message
    assert "250 failed" in message
    assert "Download error log" in message


@pytest.mark.unit
def test_format_error_summary_all_failed():
    """Test error summary when all records failed."""
    message = format_error_summary(
        total_records=100,
        processed_records=0,
        failed_records=100
    )

    assert "0 / 100" in message
    assert "100 failed" in message


@pytest.mark.unit
def test_format_error_summary_one_failure():
    """Test error summary with single failure."""
    message = format_error_summary(
        total_records=1000,
        processed_records=999,
        failed_records=1
    )

    assert "999 / 1,000" in message
    assert "1 failed" in message


@pytest.mark.unit
def test_format_error_summary_number_formatting():
    """Test that large numbers are formatted with commas."""
    message = format_error_summary(
        total_records=1234567,
        processed_records=1234560,
        failed_records=7
    )

    # Numbers should be comma-formatted
    assert "1,234,560" in message
    assert "1,234,567" in message


@pytest.mark.unit
def test_csv_content_is_bytes():
    """Test that errors_to_csv returns bytes (not string)."""
    errors = [
        create_mock_error(1, "Test error", '{"test": "data"}')
    ]

    csv_content = errors_to_csv(errors)

    # Should return bytes
    assert isinstance(csv_content, bytes)

    # Should be decodable as UTF-8
    csv_text = csv_content.decode('utf-8')
    assert isinstance(csv_text, str)


@pytest.mark.unit
def test_csv_utf8_encoding():
    """Test CSV export handles UTF-8 characters."""
    errors = [
        create_mock_error(
            row_number=1,
            error_message='Error with UTF-8: café, naïve, 日本語',
            raw_data='{"name": "José García", "city": "São Paulo"}'
        )
    ]

    csv_content = errors_to_csv(errors)
    csv_text = csv_content.decode('utf-8')

    # Should preserve UTF-8 characters
    assert 'café' in csv_text
    assert 'naïve' in csv_text
    assert '日本語' in csv_text
    assert 'José García' in csv_text
    assert 'São Paulo' in csv_text
