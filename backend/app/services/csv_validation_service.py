"""CSV content validation service."""
import logging
from typing import List, Dict
from app.utils.csv_parser import parse_csv, parse_csv_preview, CSVParseError
from app.exceptions import CSVValidationError

# Configure logger
logger = logging.getLogger(__name__)


class CSVValidationService:
    """Service for validating CSV content structure."""

    # Required columns for each CSV type (case-insensitive matching)
    # Based on PRD Epic 2, Story 2.2 Acceptance Criteria
    SKILLS_REQUIRED_COLUMNS = ["ID", "NAME", "DESCRIPTION", "CATEGORY", "SUBCATEGORY"]
    JOBS_REQUIRED_COLUMNS = ["Job ID", "Job Title", "Company Name", "Location", "standardized_skills"]

    def validate_skills_csv(self, content: bytes) -> Dict:
        """
        Validate skills CSV structure.

        Args:
            content: CSV file content

        Returns:
            dict: Parsed CSV data if valid

        Raises:
            CSVValidationError: If validation fails
        """
        return self._validate_csv(
            content,
            required_columns=self.SKILLS_REQUIRED_COLUMNS,
            csv_type="Skills"
        )

    def validate_jobs_csv(self, content: bytes) -> Dict:
        """
        Validate jobs CSV structure.

        Args:
            content: CSV file content

        Returns:
            dict: Parsed CSV data if valid

        Raises:
            CSVValidationError: If validation fails
        """
        return self._validate_csv(
            content,
            required_columns=self.JOBS_REQUIRED_COLUMNS,
            csv_type="Jobs"
        )

    def _validate_csv(
        self,
        content: bytes,
        required_columns: List[str],
        csv_type: str
    ) -> Dict:
        """
        Generic CSV validation logic.

        Args:
            content: CSV file content
            required_columns: List of required column names
            csv_type: "Skills" or "Jobs" (for error messages)

        Returns:
            dict: Parsed CSV data

        Raises:
            CSVValidationError: If validation fails
        """
        file_size_mb = len(content) / (1024 * 1024)
        logger.info(f"Starting {csv_type} CSV validation. File size: {file_size_mb:.2f}MB")

        # Parse CSV
        try:
            parsed_data = parse_csv(content)
            logger.debug(f"CSV parsed successfully. Columns: {parsed_data['columns']}, Rows: {parsed_data['total_count']}")
        except CSVParseError as e:
            logger.error(f"Failed to parse {csv_type} CSV: {str(e)}")
            raise CSVValidationError(
                detail=f"Failed to parse {csv_type} CSV",
                validation_errors=[str(e)]
            )

        # Check for data rows
        if parsed_data["total_count"] == 0:
            logger.warning(f"{csv_type} CSV contains no data rows (header only)")
            raise CSVValidationError(
                detail="CSV file contains no data rows",
                validation_errors=["CSV has header row but no data"]
            )

        # Check for required columns (case-insensitive)
        csv_columns_lower = [col.lower().strip() for col in parsed_data["columns"]]
        required_columns_lower = [col.lower() for col in required_columns]

        missing_columns = []
        for required_col in required_columns_lower:
            if required_col not in csv_columns_lower:
                # Find original casing for error message
                original_name = next(
                    (col for col in required_columns if col.lower() == required_col),
                    required_col
                )
                missing_columns.append(original_name)

        if missing_columns:
            logger.warning(
                f"{csv_type} CSV validation failed. Missing columns: {missing_columns}. "
                f"Found: {parsed_data['columns']}"
            )
            raise CSVValidationError(
                detail=f"Missing required columns in {csv_type} CSV",
                validation_errors=[
                    f"Required columns: {', '.join(required_columns)}",
                    f"Missing columns: {', '.join(missing_columns)}",
                    f"Found columns: {', '.join(parsed_data['columns'])}"
                ]
            )

        logger.info(
            f"{csv_type} CSV validation successful. "
            f"Rows: {parsed_data['total_count']}, Columns: {len(parsed_data['columns'])}"
        )
        return parsed_data

    def validate_and_preview_skills(
        self,
        content: bytes,
        preview_rows: int = 10
    ) -> Dict:
        """
        Validate skills CSV and return preview data.

        This method is used for Story 2.3 CSV preview functionality.
        It validates CSV structure and returns first N rows for user confirmation.

        Args:
            content: CSV file content
            preview_rows: Number of rows to preview (default: 10)

        Returns:
            dict: {
                "is_valid": bool,
                "columns": List[str],
                "preview_rows": List[dict],
                "total_rows": int,
                "has_more": bool,
                "validation_errors": List[str]  # Empty if valid
            }

        Raises:
            CSVValidationError: If validation fails
        """
        return self._validate_and_preview(
            content,
            required_columns=self.SKILLS_REQUIRED_COLUMNS,
            csv_type="Skills",
            preview_rows=preview_rows
        )

    def validate_and_preview_jobs(
        self,
        content: bytes,
        preview_rows: int = 10
    ) -> Dict:
        """
        Validate jobs CSV and return preview data.

        This method is used for Story 2.3 CSV preview functionality.
        It validates CSV structure and returns first N rows for user confirmation.

        Args:
            content: CSV file content
            preview_rows: Number of rows to preview (default: 10)

        Returns:
            dict: Preview data with validation status

        Raises:
            CSVValidationError: If validation fails
        """
        return self._validate_and_preview(
            content,
            required_columns=self.JOBS_REQUIRED_COLUMNS,
            csv_type="Jobs",
            preview_rows=preview_rows
        )

    def _validate_and_preview(
        self,
        content: bytes,
        required_columns: List[str],
        csv_type: str,
        preview_rows: int
    ) -> Dict:
        """
        Generic CSV validation and preview logic.

        Args:
            content: CSV file content
            required_columns: List of required column names
            csv_type: "Skills" or "Jobs" (for error messages)
            preview_rows: Number of rows to preview

        Returns:
            dict: Preview data with validation status

        Raises:
            CSVValidationError: If validation fails
        """
        file_size_mb = len(content) / (1024 * 1024)
        logger.info(
            f"Starting {csv_type} CSV validation and preview. "
            f"File size: {file_size_mb:.2f}MB, Preview rows: {preview_rows}"
        )

        # Parse CSV with preview (more efficient than parsing full CSV)
        try:
            preview_data = parse_csv_preview(content, preview_rows)
            logger.debug(
                f"CSV preview parsed successfully. "
                f"Columns: {preview_data['columns']}, Total rows: {preview_data['total_rows']}, "
                f"Preview rows: {len(preview_data['preview_rows'])}"
            )
        except CSVParseError as e:
            logger.error(f"Failed to parse {csv_type} CSV for preview: {str(e)}")
            raise CSVValidationError(
                detail=f"Failed to parse {csv_type} CSV",
                validation_errors=[str(e)]
            )

        # Check for data rows
        if preview_data["total_rows"] == 0:
            logger.warning(f"{csv_type} CSV contains no data rows (header only)")
            raise CSVValidationError(
                detail="CSV file contains no data rows",
                validation_errors=["CSV has header row but no data"]
            )

        # Check for required columns (case-insensitive)
        csv_columns_lower = [col.lower().strip() for col in preview_data["columns"]]
        required_columns_lower = [col.lower() for col in required_columns]

        missing_columns = []
        for required_col in required_columns_lower:
            if required_col not in csv_columns_lower:
                # Find original casing for error message
                original_name = next(
                    (col for col in required_columns if col.lower() == required_col),
                    required_col
                )
                missing_columns.append(original_name)

        if missing_columns:
            logger.warning(
                f"{csv_type} CSV validation failed. Missing columns: {missing_columns}. "
                f"Found: {preview_data['columns']}"
            )
            raise CSVValidationError(
                detail=f"Missing required columns in {csv_type} CSV",
                validation_errors=[
                    f"Required columns: {', '.join(required_columns)}",
                    f"Missing columns: {', '.join(missing_columns)}",
                    f"Found columns: {', '.join(preview_data['columns'])}"
                ]
            )

        # Validation successful
        logger.info(
            f"{csv_type} CSV validation and preview successful. "
            f"Total rows: {preview_data['total_rows']}, "
            f"Preview rows: {len(preview_data['preview_rows'])}, "
            f"Columns: {len(preview_data['columns'])}"
        )

        return {
            "is_valid": True,
            "columns": preview_data["columns"],
            "preview_rows": preview_data["preview_rows"],
            "total_rows": preview_data["total_rows"],
            "has_more": preview_data["has_more"],
            "validation_errors": []
        }
