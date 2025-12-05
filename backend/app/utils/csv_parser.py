"""CSV parsing utilities."""
import pandas as pd
import io
import logging
import ast
from typing import Dict, List, Any, Union

# Configure logger
logger = logging.getLogger(__name__)


class CSVParseError(Exception):
    """Raised when CSV file cannot be parsed."""
    pass


def parse_list_field(value: Any) -> List[Any]:
    """
    Parse a CSV field that contains a list representation.

    Handles cases like:
    - "[None, 'Java 8', 'Java']" -> [None, 'Java 8', 'Java']
    - "['Python', 'Django']" -> ['Python', 'Django']
    - None or empty string -> []
    - Already a list -> return as is

    Args:
        value: CSV cell value that may contain a list

    Returns:
        Parsed list, or empty list if value is None/empty/invalid
    """
    # Handle None, NaN, empty string
    if pd.isna(value) or value is None or value == "":
        return []

    # If already a list, return it
    if isinstance(value, list):
        return value

    # Convert to string and try to parse
    if not isinstance(value, str):
        value = str(value)

    # Remove whitespace
    value = value.strip()

    # Empty string after strip
    if not value:
        return []

    try:
        # Try to parse as Python literal (handles [None, 'str', 123, etc])
        parsed = ast.literal_eval(value)

        # If result is a list, return it
        if isinstance(parsed, list):
            # Filter out None values
            return [item for item in parsed if item is not None]
        else:
            # Single value, wrap in list
            return [parsed] if parsed is not None else []

    except (ValueError, SyntaxError) as e:
        # If parsing fails, treat as single string value
        logger.warning(f"Failed to parse list field: {value[:50]}... Error: {e}")
        return [value]


def sanitize_csv_value(value: Any) -> Any:
    """
    Sanitize CSV cell value to prevent formula injection attacks.

    CSV injection (aka Formula injection) occurs when data starting with
    special characters (=, +, -, @, |, %) is interpreted as formulas
    by spreadsheet applications like Excel or Google Sheets.

    Args:
        value: Cell value to sanitize

    Returns:
        Sanitized value with dangerous formulas prefixed with single quote
    """
    # Handle NaN, None, and other non-string types
    if pd.isna(value) or value is None:
        return ""

    # Convert to string if not already
    if not isinstance(value, str):
        value = str(value)

    # Check if value starts with formula-like characters
    dangerous_chars = ('=', '+', '-', '@', '|', '%')
    if value.strip().startswith(dangerous_chars):
        # Prefix with single quote to prevent formula execution
        sanitized = "'" + value
        logger.debug(f"Sanitized potential formula injection: {value[:20]}... -> {sanitized[:20]}...")
        return sanitized

    return value


def sanitize_csv_data(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sanitize all values in CSV data rows.

    Args:
        rows: List of dictionaries representing CSV rows

    Returns:
        List of dictionaries with sanitized values
    """
    sanitized_rows = []
    for row in rows:
        sanitized_row = {key: sanitize_csv_value(value) for key, value in row.items()}
        sanitized_rows.append(sanitized_row)
    return sanitized_rows


def parse_csv(content: bytes) -> Dict:
    """
    Parse CSV file content with security sanitization.

    Args:
        content: CSV file content as bytes

    Returns:
        dict: {
            "columns": List[str],  # Column names
            "rows": List[dict],    # All data rows (sanitized)
            "total_count": int     # Total row count
        }

    Raises:
        CSVParseError: If CSV cannot be parsed
    """
    logger.debug(f"Parsing CSV content. Size: {len(content)} bytes")

    try:
        # Try UTF-8 encoding first
        df = pd.read_csv(io.BytesIO(content), encoding='utf-8')
        logger.debug("CSV parsed successfully with UTF-8 encoding")
    except UnicodeDecodeError:
        # Fallback to latin-1 encoding
        logger.debug("UTF-8 decode failed, trying latin-1 encoding")
        try:
            df = pd.read_csv(io.BytesIO(content), encoding='latin-1')
            logger.debug("CSV parsed successfully with latin-1 encoding")
        except (pd.errors.ParserError, ValueError) as e:
            logger.error(f"Failed to decode CSV file with latin-1: {str(e)}")
            raise CSVParseError(f"Failed to decode CSV file: {str(e)}")
    except pd.errors.EmptyDataError:
        logger.warning("CSV file is empty")
        raise CSVParseError("CSV file is empty")
    except pd.errors.ParserError as e:
        logger.error(f"CSV parser error: {str(e)}")
        raise CSVParseError(f"Failed to parse CSV: {str(e)}")
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"Unexpected error parsing CSV: {type(e).__name__}: {str(e)}")
        raise CSVParseError(f"Failed to parse CSV: {str(e)}")

    # Convert DataFrame to dict format
    rows = df.to_dict(orient='records')

    # Sanitize data to prevent CSV injection
    sanitized_rows = sanitize_csv_data(rows)

    logger.info(f"CSV parsing complete. Columns: {len(df.columns)}, Rows: {len(df)}")

    return {
        "columns": df.columns.tolist(),
        "rows": sanitized_rows,
        "total_count": len(df)
    }


def parse_csv_preview(content: bytes, preview_rows: int = 10) -> Dict:
    """
    Parse CSV file and return preview with first N rows (sanitized).

    This function is used for CSV preview functionality (Story 2.3)
    to show users a sample of their data before confirming ingestion.

    Args:
        content: CSV file content as bytes
        preview_rows: Number of rows to include in preview (default: 10)

    Returns:
        dict: {
            "columns": List[str],        # Column names
            "preview_rows": List[dict],  # First N data rows (sanitized)
            "total_rows": int,           # Total row count
            "has_more": bool             # True if total_rows > preview_rows
        }

    Raises:
        CSVParseError: If CSV cannot be parsed
    """
    logger.debug(f"Parsing CSV preview. Size: {len(content)} bytes, Preview rows: {preview_rows}")

    try:
        # Try UTF-8 encoding first
        df = pd.read_csv(io.BytesIO(content), encoding='utf-8')
        logger.debug("CSV parsed successfully with UTF-8 encoding for preview")
    except UnicodeDecodeError:
        # Fallback to latin-1 encoding
        logger.debug("UTF-8 decode failed for preview, trying latin-1 encoding")
        try:
            df = pd.read_csv(io.BytesIO(content), encoding='latin-1')
            logger.debug("CSV parsed successfully with latin-1 encoding for preview")
        except (pd.errors.ParserError, ValueError) as e:
            logger.error(f"Failed to decode CSV file for preview with latin-1: {str(e)}")
            raise CSVParseError(f"Failed to decode CSV file: {str(e)}")
    except pd.errors.EmptyDataError:
        logger.warning("CSV file is empty for preview")
        raise CSVParseError("CSV file is empty")
    except pd.errors.ParserError as e:
        logger.error(f"CSV parser error for preview: {str(e)}")
        raise CSVParseError(f"Failed to parse CSV: {str(e)}")
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"Unexpected error parsing CSV preview: {type(e).__name__}: {str(e)}")
        raise CSVParseError(f"Failed to parse CSV: {str(e)}")

    total_rows = len(df)

    # Get first N rows for preview
    preview_df = df.head(preview_rows)
    preview_data = preview_df.to_dict(orient='records')

    # IMPORTANT: Sanitize preview rows to prevent CSV injection
    # This protects against formula execution in Excel/Google Sheets
    sanitized_preview = sanitize_csv_data(preview_data)

    logger.info(
        f"CSV preview generation complete. Total rows: {total_rows}, "
        f"Preview rows: {len(sanitized_preview)}, Columns: {len(df.columns)}"
    )

    return {
        "columns": df.columns.tolist(),
        "preview_rows": sanitized_preview,  # Sanitized data
        "total_rows": total_rows,
        "has_more": total_rows > preview_rows
    }
