class CSVValidationError(Exception):
    """Raised when CSV validation fails."""
    def __init__(self, message: str, errors: list = None):
        self.message = message
        self.errors = errors or []
        super().__init__(self.message)
