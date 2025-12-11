class AuthenticationError(Exception):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Authentication failed"):
        self.message = message
        super().__init__(self.message)

class AuthorizationError(Exception):
    """Raised when user is not authorized to perform an action."""
    def __init__(self, message: str = "Not authorized"):
        self.message = message
        super().__init__(self.message)
