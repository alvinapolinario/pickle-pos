"""Domain-specific exceptions shared across Django and FastAPI."""


class DomainError(Exception):
    """Base class for business rule violations."""

    def __init__(self, message: str, code: str = "domain_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class AuthenticationError(DomainError):
    def __init__(self, message: str = "Invalid credentials") -> None:
        super().__init__(message, code="authentication_error")


class AuthorizationError(DomainError):
    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message, code="authorization_error")


class NotFoundError(DomainError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code="not_found")


class ConflictError(DomainError):
    def __init__(self, message: str = "Conflict detected") -> None:
        super().__init__(message, code="conflict")


class InsufficientStockError(DomainError):
    def __init__(self, message: str = "Insufficient stock") -> None:
        super().__init__(message, code="insufficient_stock")
