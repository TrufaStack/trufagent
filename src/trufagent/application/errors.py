class CartographyUnavailableError(RuntimeError):
    """Raised when structural context cannot be safely queried."""


class SafeAdapterError(RuntimeError):
    """Adapter failure whose closed diagnostic code is safe to surface."""

    diagnostic_code: str
