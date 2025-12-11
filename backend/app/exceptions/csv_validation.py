from fastapi import HTTPException, status

class CSVValidationError(HTTPException):
    """Raised when CSV validation fails."""
    def __init__(self, detail: str, validation_errors: list = None):
        if validation_errors:
            error_details = "; ".join([str(e) for e in validation_errors])
            detail = f"{detail}: {error_details}"
        
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )
