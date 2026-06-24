from decimal import Decimal

from django.utils import timezone

from promotions.exceptions import (PromoAlreadyUsedError, PromoExpiredError,
                                   PromoLimitExceededError,
                                   PromoNotApplicableError, PromoNotFoundError)
from promotions.models import PromoCode, PromoCodeUsage
from users.models import User


class PromoService:
    """Service for promo code validation and discount calculation."""

    @staticmethod
    def get_promo(code: str) -> PromoCode:
        """
        Retrieve promo code by code value.

        Raises:
            PromoNotFoundError
        """
        try:
            return PromoCode.objects.prefetch_related("categories").get(
                code=code
            )
        except PromoCode.DoesNotExist as exc:
            raise PromoNotFoundError from exc

    @staticmethod
    def validate_promo(
        *,
        promo: PromoCode,
        user: User,
    ) -> None:
        """
        Validate promo code availability.

        Checks:
        - expiration date;
        - usage limit;
        - user has not used promo before.

        Raises:
            PromoExpiredError
            PromoLimitExceededError
            PromoAlreadyUsedError
        """
        now = timezone.now()

        if promo.expires_at <= now:
            raise PromoExpiredError

        if promo.usages_count >= promo.max_usages:
            raise PromoLimitExceededError

        already_used = PromoCodeUsage.objects.filter(
            user=user,
            promo_code=promo,
        ).exists()

        if already_used:
            raise PromoAlreadyUsedError

    @staticmethod
    def get_eligible_items(
        *,
        promo: PromoCode,
        items: list,
    ) -> list:
        """
        Return order items eligible for promo discount.

        Rules:
        - promo_excluded goods are skipped;
        - if promo has no categories -> all categories allowed;
        - otherwise only goods from allowed categories.

        Returns:
            list of eligible items

        Raises:
            PromoNotApplicableError
        """
        category_ids = set(
            promo.categories.values_list("id", flat=True)
        )

        applies_to_all_categories = not category_ids

        eligible_items = []

        for item in items:
            good = item.good

            if good.promo_excluded:
                continue

            if applies_to_all_categories:
                eligible_items.append(item)
                continue

            if good.category_id in category_ids:
                eligible_items.append(item)

        if not eligible_items:
            raise PromoNotApplicableError

        return eligible_items

    @staticmethod
    def calculate_discount(
        *,
        promo: PromoCode,
        items: list,
    ) -> Decimal:
        """
        Calculate discount amount in money.

        IMPORTANT:
        quantity is taken into account.

        Returns:
            Decimal discount amount
        """
        discount_amount = Decimal("0")

        percent = promo.discount_percent / Decimal("100")

        for item in items:
            line_total = item.good.price * item.quantity
            discount_amount += line_total * percent

        return discount_amount.quantize(
            Decimal("0.01")
        )
