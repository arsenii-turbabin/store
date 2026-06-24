class OrderError(Exception):
    """Base exception for order-related errors."""

    default_message = "Order error"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)


class EmptyOrderError(OrderError):
    """Raised when order contains no items."""

    default_message = "Order must contain at least one item"


class InvalidQuantityError(OrderError):
    """Raised when item quantity is invalid."""

    default_message = "Invalid item quantity"


class GoodNotFoundError(OrderError):
    """Raised when requested good does not exist."""

    default_message = "Good not found"


class DuplicateGoodError(OrderError):
    """Raised when the same good appears multiple times in order."""

    default_message = "Duplicate goods are not allowed in order"
