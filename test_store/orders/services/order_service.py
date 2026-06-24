from decimal import Decimal
from typing import Iterable

from django.db import models, transaction

from catalog.models import Good
from orders.exceptions import (DuplicateGoodError, EmptyOrderError,
                               GoodNotFoundError, InvalidQuantityError)
from orders.models import Order, OrderItem
from promotions.models import PromoCode, PromoCodeUsage
from promotions.services import PromoService
from users.models import User


class OrderService:
    """Service for order creation and management."""

    class CreateOrderItemData:
        """Data transfer object for an order item creation request."""

        __slots__ = ("good_id", "quantity")

        def __init__(self, good_id: int, quantity: int) -> None:
            self.good_id = good_id
            self.quantity = quantity

    @classmethod
    def create_order(
        cls,
        *,
        user: User,
        items: Iterable[CreateOrderItemData],
        promo_code: str | None = None,
    ) -> Order:
        """
        Create an order with optional promo code application.

        Args:
            user: The user placing the order.
            items: Iterable of CreateOrderItemData with good_id and quantity.
            promo_code: Optional promo code string.

        Returns:
            The created Order instance with prefetched items.

        Raises:
            EmptyOrderError: If no items provided.
            InvalidQuantityError: If any item has non-positive quantity.
            GoodNotFoundError: If a good does not exist.
            DuplicateGoodError: If the same good appears multiple times.
            PromoError: If promo code validation fails.
        """
        items = list(items)

        cls._validate_items(items)

        goods_map = cls._fetch_goods(items)

        with transaction.atomic():
            order = cls._build_order(
                user=user,
                items=items,
                goods_map=goods_map,
            )

            if promo_code:
                cls._apply_promo(
                    order=order,
                    user=user,
                    promo_code=promo_code,
                )

        order = Order.objects.select_related("promo_code").prefetch_related(
            "items__good",
            "items__good__category",
        ).get(pk=order.pk)

        return order

    @classmethod
    def _validate_items(
        cls,
        items: list[CreateOrderItemData],
    ) -> None:
        """Validate order items before processing."""
        if not items:
            raise EmptyOrderError

        good_ids_seen = set()

        for item in items:
            if item.quantity <= 0:
                raise InvalidQuantityError

            if item.good_id in good_ids_seen:
                raise DuplicateGoodError

            good_ids_seen.add(item.good_id)

    @classmethod
    def _fetch_goods(
        cls,
        items: list[CreateOrderItemData],
    ) -> dict[int, Good]:
        """
        Fetch goods from DB and validate they exist.

        Returns:
            Mapping of good_id -> Good instance.

        Raises:
            GoodNotFoundError: If any good is missing.
        """
        good_ids = {item.good_id for item in items}
        goods = Good.objects.filter(id__in=good_ids)
        goods_map = {g.id: g for g in goods}

        for good_id in good_ids:
            if good_id not in goods_map:
                raise GoodNotFoundError(
                    f"Good with id={good_id} not found",
                )

        return goods_map

    @classmethod
    def _build_order(
        cls,
        *,
        user: User,
        items: list[CreateOrderItemData],
        goods_map: dict[int, Good],
    ) -> Order:
        """Create Order and OrderItem records without promo discount."""
        price = Decimal("0")

        order = Order.objects.create(
            user=user,
            price=Decimal("0"),
            discount=Decimal("0"),
            total=Decimal("0"),
        )

        order_items_to_create = []

        for item in items:
            good = goods_map[item.good_id]
            line_total = good.price * item.quantity
            price += line_total

            order_items_to_create.append(
                OrderItem(
                    order=order,
                    good=good,
                    quantity=item.quantity,
                    price=good.price,
                    discount=Decimal("0"),
                    total=line_total,
                ),
            )

        OrderItem.objects.bulk_create(order_items_to_create)

        order.price = price
        order.total = price
        order.save(update_fields=("price", "total"))

        return order

    @classmethod
    def _apply_promo(
        cls,
        *,
        order: Order,
        user: User,
        promo_code: str,
    ) -> None:
        """
        Apply promo code to an existing order.

        Validates the promo, calculates discount, updates order
        and order items, records usage, and increments counter.

        Raises:
            PromoError: On any promo validation failure.
        """
        promo = PromoService.get_promo(promo_code)
        PromoService.validate_promo(promo=promo, user=user)

        order_items = list(order.items.select_related("good__category"))

        eligible_items = PromoService.get_eligible_items(
            promo=promo,
            items=order_items,
        )

        discount_amount = PromoService.calculate_discount(
            promo=promo,
            items=eligible_items,
        )

        cls._apply_discount_to_items(
            eligible_items=eligible_items,
            discount_amount=discount_amount,
            order_price=order.price,
        )

        order.discount = discount_amount
        order.total = order.price - discount_amount
        order.promo_code = promo
        order.save(update_fields=("discount", "total", "promo_code"))

        PromoCodeUsage.objects.create(
            user=user,
            promo_code=promo,
            order=order,
        )

        PromoCode.objects.filter(pk=promo.pk).update(
            usages_count=models.F("usages_count") + 1,
        )

    @classmethod
    def _apply_discount_to_items(
        cls,
        *,
        eligible_items: list[OrderItem],
        discount_amount: Decimal,
        order_price: Decimal,
    ) -> None:
        """
        Distribute discount proportionally across eligible items.

        Uses proportional distribution based on each item's
        line total relative to the total price of eligible items.
        """
        if not eligible_items or discount_amount == Decimal("0"):
            return

        eligible_total = sum(
            item.good.price * item.quantity
            for item in eligible_items
        )

        if eligible_total == Decimal("0"):
            return

        distributed = Decimal("0")
        items_to_update = []

        for i, item in enumerate(eligible_items):
            line_total = item.good.price * item.quantity
            item_discount = (
                discount_amount * line_total / eligible_total
            ).quantize(Decimal("0.01"))

            # Last item gets the remainder to avoid rounding issues
            if i == len(eligible_items) - 1:
                item_discount = discount_amount - distributed

            item.discount = item_discount
            item.total = line_total - item_discount
            distributed += item_discount
            items_to_update.append(item)

        OrderItem.objects.bulk_update(
            items_to_update,
            fields=("discount", "total"),
        )
