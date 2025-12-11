from fastapi import HTTPException, status

class AuthenticationError(HTTPException):
    """Raised when authentication fails."""
    def __init__(self, detail: str = "Authentication failed", headers: dict = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers=headers
        )

class AuthorizationError(HTTPException):
    """Raised when user is not authorized to perform an action."""
    def __init__(self, detail: str = "Not authorized", headers: dict = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            headers=headers
        )
