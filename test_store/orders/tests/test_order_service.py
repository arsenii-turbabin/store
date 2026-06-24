from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from catalog.models import Good
from orders.exceptions import (DuplicateGoodError, EmptyOrderError,
                               GoodNotFoundError, InvalidQuantityError)
from orders.services import OrderService
from promotions.exceptions import (PromoAlreadyUsedError, PromoExpiredError,
                                   PromoLimitExceededError,
                                   PromoNotApplicableError)
from promotions.models import PromoCode, PromoCodeUsage


def make_item(good_id: int, quantity: int = 1):
    return OrderService.CreateOrderItemData(
        good_id=good_id,
        quantity=quantity,
    )


class TestCreateOrderWithoutPromo:
    """OrderService.create_order — no promo code."""

    def test_single_item(self, user, good):
        order = OrderService.create_order(
            user=user,
            items=[make_item(good.id, 2)],
        )
        expected_price = good.price * 2
        assert order.price == expected_price
        assert order.total == expected_price
        assert order.discount == Decimal("0")
        assert order.user == user

        item = order.items.first()
        assert item.good == good
        assert item.quantity == 2
        assert item.total == expected_price

    def test_multiple_items(self, user, good, good2):
        order = OrderService.create_order(
            user=user,
            items=[
                make_item(good.id, 1),
                make_item(good2.id, 3),
            ],
        )
        expected_price = good.price * 1 + good2.price * 3
        assert order.price == expected_price
        assert order.total == expected_price
        assert order.items.count() == 2

    def test_empty_order_raises_error(self, user):
        with pytest.raises(EmptyOrderError):
            OrderService.create_order(user=user, items=[])

    def test_zero_quantity_raises_error(self, user, good):
        with pytest.raises(InvalidQuantityError):
            OrderService.create_order(
                user=user,
                items=[make_item(good.id, 0)],
            )

    def test_negative_quantity_raises_error(self, user, good):
        with pytest.raises(InvalidQuantityError):
            OrderService.create_order(
                user=user,
                items=[make_item(good.id, -1)],
            )

    def test_duplicate_good_raises_error(self, user, good):
        with pytest.raises(DuplicateGoodError):
            OrderService.create_order(
                user=user,
                items=[
                    make_item(good.id, 1),
                    make_item(good.id, 2),
                ],
            )

    def test_nonexistent_good_raises_error(self, user):
        with pytest.raises(GoodNotFoundError):
            OrderService.create_order(
                user=user,
                items=[make_item(99999, 1)],
            )


class TestCreateOrderWithPromo:
    """OrderService.create_order — with promo code."""

    def test_promo_applies_discount(self, user, good, promo):
        order = OrderService.create_order(
            user=user,
            items=[make_item(good.id, 1)],
            promo_code="SAVE10",
        )
        expected_discount = (good.price * promo.discount_percent / 100).quantize(
            Decimal("0.01")
        )
        expected_total = good.price - expected_discount

        assert order.discount == expected_discount
        assert order.total == expected_total
        assert order.promo_code == promo

    def test_discount_distribution_proportional(self, user, good, good2, promo):
        order = OrderService.create_order(
            user=user,
            items=[
                make_item(good.id, 1),   # 1000
                make_item(good2.id, 1),  # 500
            ],
            promo_code="SAVE10",
        )
        expected_discount = (
            (good.price + good2.price) * promo.discount_percent / 100
        ).quantize(Decimal("0.01"))
        assert order.discount == expected_discount
        assert order.total == good.price + good2.price - expected_discount

        items = list(order.items.order_by("id"))
        # Item1 share: 1000/1500 * 150 = 100.00
        assert items[0].discount == Decimal("100.00")
        assert items[0].total == Decimal("900.00")
        # Item2 share: 500/1500 * 150 = 50.00
        assert items[1].discount == Decimal("50.00")
        assert items[1].total == Decimal("450.00")

    def test_promo_usage_recorded(self, user, good, promo):
        OrderService.create_order(
            user=user,
            items=[make_item(good.id, 1)],
            promo_code="SAVE10",
        )
        assert PromoCodeUsage.objects.filter(
            user=user,
            promo_code=promo,
        ).exists()

    def test_promo_usages_count_incremented(self, user, good, promo):
        OrderService.create_order(
            user=user,
            items=[make_item(good.id, 1)],
            promo_code="SAVE10",
        )
        promo.refresh_from_db()
        assert promo.usages_count == 1

    def test_expired_promo_raises_error(self, user, good):
        PromoCode.objects.create(
            code="EXPIRED",
            discount_percent=Decimal("10.00"),
            max_usages=100,
            expires_at=timezone.now() - timedelta(days=1),
        )
        with pytest.raises(PromoExpiredError):
            OrderService.create_order(
                user=user,
                items=[make_item(good.id, 1)],
                promo_code="EXPIRED",
            )

    def test_promo_used_twice_by_same_user(self, user, good, good2, promo):
        OrderService.create_order(
            user=user,
            items=[make_item(good.id, 1)],
            promo_code="SAVE10",
        )
        with pytest.raises(PromoAlreadyUsedError):
            OrderService.create_order(
                user=user,
                items=[make_item(good2.id, 1)],
                promo_code="SAVE10",
            )

    def test_max_usages_reached(self, user, good, half_used_promo):
        """Using a promo that has reached its usage limit raises error."""
        OrderService.create_order(
            user=user,
            items=[make_item(good.id, 1)],
            promo_code="HALF",
        )
        # Second usage should exceed the limit
        with pytest.raises(PromoLimitExceededError):
            OrderService.create_order(
                user=user,
                items=[make_item(good.id, 1)],
                promo_code="HALF",
            )

    def test_nonexistent_promo_raises_error(self, user, good):
        from promotions.exceptions import PromoNotFoundError

        with pytest.raises(PromoNotFoundError):
            OrderService.create_order(
                user=user,
                items=[make_item(good.id, 1)],
                promo_code="DOES_NOT_EXIST",
            )

    def test_promo_excluded_good_skipped(self, user, category, good, promo):
        excluded = Good.objects.create(
            name="ExcludedItem",
            category=category,
            price=Decimal("200.00"),
            promo_excluded=True,
        )
        order = OrderService.create_order(
            user=user,
            items=[
                make_item(good.id, 1),
                make_item(excluded.id, 1),
            ],
            promo_code="SAVE10",
        )
        expected_discount = (good.price * promo.discount_percent / 100).quantize(
            Decimal("0.01")
        )
        assert order.discount == expected_discount
        assert order.total == good.price + excluded.price - expected_discount

    def test_promo_with_category_restriction(self, user, good, other_category, promo):
        other_good = Good.objects.create(
            name="T-Shirt",
            category=other_category,
            price=Decimal("50.00"),
            promo_excluded=False,
        )
        promo.categories.add(good.category)

        order = OrderService.create_order(
            user=user,
            items=[
                make_item(good.id, 1),
                make_item(other_good.id, 2),
            ],
            promo_code="SAVE10",
        )
        expected_discount = (good.price * promo.discount_percent / 100).quantize(
            Decimal("0.01")
        )
        assert order.discount == expected_discount
        assert order.total == good.price + other_good.price * 2 - expected_discount

    def test_promo_not_applicable_raises_error(self, user, category, promo):
        excluded = Good.objects.create(
            name="Excluded",
            category=category,
            price=Decimal("100.00"),
            promo_excluded=True,
        )
        with pytest.raises(PromoNotApplicableError):
            OrderService.create_order(
                user=user,
                items=[make_item(excluded.id, 1)],
                promo_code="SAVE10",
            )
