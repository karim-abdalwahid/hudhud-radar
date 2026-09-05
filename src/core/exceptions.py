"""
Custom Exception Classes for SocailManager.
"""


class SocailManagerException(Exception):
    """Base exception for all SocailManager errors."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class MetaAPIError(SocailManagerException):
    """Raised when an error occurs while communicating with Meta Graph API."""
    def __init__(self, message: str, status_code: int = None, error_subcode: int = None, details: dict = None):
        super().__init__(message, details)
        self.status_code = status_code
        self.error_subcode = error_subcode


class RateLimitExceededError(SocailManagerException):
    """Raised when request rate limits for Facebook/Instagram are reached."""
    def __init__(self, platform: str, retry_after: int = 60, details: dict = None):
        super().__init__(f"Rate limit exceeded on {platform}. Retry after {retry_after}s.", details)
        self.platform = platform
        self.retry_after = retry_after


class MessagingWindowExpiredError(SocailManagerException):
    """Raised when attempting to message a user outside the 24-hour standard window without approval."""
    def __init__(self, recipient_id: str, elapsed_hours: float, details: dict = None):
        super().__init__(
            f"24-Hour Messaging Window expired for recipient {recipient_id} ({elapsed_hours:.1f}h elapsed).",
            details
        )
        self.recipient_id = recipient_id
        self.elapsed_hours = elapsed_hours


class IdentityResolutionError(SocailManagerException):
    """Raised when identity resolution encounters ambiguity or conflict."""
    pass


class ComplianceViolationError(SocailManagerException):
    """Raised when an action would violate platform Terms of Service, privacy, or anti-spam rules."""
    pass


class DatabaseConnectionError(SocailManagerException):
    """Raised when unable to connect or sync with Supabase PostgreSQL."""
    pass
