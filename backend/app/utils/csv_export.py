"""CSV export utilities for error logs."""

import csv
import io
from typing import List
from prisma.models import IngestionError


def errors_to_csv(errors: List[IngestionError]) -> bytes:
    """
    Convert ingestion errors to CSV format.

    Args:
        errors: List of IngestionError model instances

    Returns:
        CSV file content as bytes

    CSV Format:
        row_number,error_message,raw_data
        15,"Missing required field: NAME","{""ID"": ""123"", ""DESCRIPTION"": ""...""}"
        42,"Invalid data type: LEVEL must be integer","..."

    Example:
        >>> errors = await error_service.get_job_errors("job-123")
        >>> csv_bytes = errors_to_csv(errors)
        >>> # Download or save csv_bytes
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)

    # Write header
    writer.writerow(["row_number", "error_message", "raw_data"])

    # Write error rows
    for error in errors:
        writer.writerow([
            error.row_number,
            error.error_message,
            error.raw_data  # Already JSON string from database
        ])

    # Convert to bytes (UTF-8 encoding)
    csv_content = output.getvalue()
    return csv_content.encode('utf-8')


def format_error_summary(
    total_records: int,
    processed_records: int,
    failed_records: int
) -> str:
    """
    Format partial success message for user.

    Args:
        total_records: Total CSV records
        processed_records: Successfully processed records
        failed_records: Failed records

    Returns:
        Formatted success message

    Examples:
        >>> format_error_summary(40523, 40523, 0)
        'All 40,523 records ingested successfully.'

        >>> format_error_summary(40523, 40518, 5)
        '40,518 / 40,523 records ingested successfully (5 failed). Download error log to review failures.'
    """
    if failed_records == 0:
        return f"All {processed_records:,} records ingested successfully."

    return (
        f"{processed_records:,} / {total_records:,} records ingested successfully "
        f"({failed_records:,} failed). Download error log to review failures."
    )
