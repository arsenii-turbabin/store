class PromoError(Exception):
    """Base exception for promo-related errors."""

    default_message = "Promo code error"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)


class PromoNotFoundError(PromoError):
    """Raised when promo code does not exist."""

    default_message = "Promo code not found"


class PromoExpiredError(PromoError):
    """Raised when promo code is expired or not yet active."""

    default_message = "Promo code is expired"


class PromoInactiveError(PromoError):
    """Raised when promo code is disabled."""

    default_message = "Promo code is inactive"


class PromoLimitExceededError(PromoError):
    """Raised when global usage limit is reached."""

    default_message = "Promo code usage limit exceeded"


class PromoAlreadyUsedError(PromoError):
    """Raised when user already used this promo code."""

    default_message = "You have already used this promo code"


class PromoNotApplicableError(PromoError):
    """Raised when promo code cannot be applied to order items."""

    default_message = "Promo code cannot be applied to your order"
