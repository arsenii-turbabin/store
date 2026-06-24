from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from catalog.models import Good
from orders.models import Order
from promotions.models import PromoCode, PromoCodeUsage
from users.models import User


class TestCreateOrderAPI:
    """Tests for POST /api/orders/."""

    @pytest.fixture(autouse=True)
    def _setup(self, api_client):
        self.client = api_client
        self.url = reverse("order-create")

    def test_success(self, user, good):
        payload = {
            "goods": [{"good_id": good.id, "quantity": 2}],
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        # DB — order was created
        order = Order.objects.get()
        expected_price = good.price * 2
        assert order.price == expected_price
        assert order.total == expected_price
        assert order.discount == Decimal("0")
        assert order.user == user

        # Response format
        data = response.data
        assert data["order_id"] == order.id
        assert data["user_id"] == user.id
        assert Decimal(data["price"]) == expected_price
        assert Decimal(data["total"]) == expected_price
        assert data["discount"] == "0"
        assert len(data["goods"]) == 1

        g = data["goods"][0]
        assert g["good_id"] == good.id
        assert g["quantity"] == 2
        assert Decimal(g["price"]) == good.price
        assert Decimal(g["total"]) == good.price * 2

    def test_with_promo(self, user, good, promo):
        payload = {
            "promo_code": "SAVE10",
            "goods": [{"good_id": good.id, "quantity": 1}],
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        # DB — promo was applied
        order = Order.objects.get()
        assert order.promo_code == promo
        expected_discount = (
            good.price * promo.discount_percent / 100
        ).quantize(Decimal("0.01"))
        expected_total = good.price - expected_discount
        assert order.discount == expected_discount
        assert order.total == expected_total

        # DB — usage was recorded
        assert PromoCodeUsage.objects.filter(
            user=user,
            promo_code=promo,
            order=order,
        ).exists()

        # DB — usages counter was incremented
        promo.refresh_from_db()
        assert promo.usages_count == 1

        # Response format
        discount_str = str(promo.discount_percent / Decimal("100"))
        data = response.data
        assert data["discount"] == discount_str
        assert Decimal(data["total"]) == expected_total

        g = data["goods"][0]
        assert Decimal(g["total"]) == good.price - expected_discount

    def test_multiple_items(self, good, good2):
        payload = {
            "goods": [
                {"good_id": good.id, "quantity": 2},
                {"good_id": good2.id, "quantity": 3},
            ],
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        # DB
        order = Order.objects.get()
        expected_price = good.price * 2 + good2.price * 3
        assert order.price == expected_price
        assert order.items.count() == 2

        # Response
        data = response.data
        assert Decimal(data["price"]) == expected_price
        assert len(data["goods"]) == 2

    def test_unauthenticated(self, good):
        from rest_framework.test import APIClient

        client = APIClient()
        payload = {
            "goods": [{"good_id": good.id, "quantity": 1}],
        }
        response = client.post(self.url, payload, format="json")
        assert response.status_code == 403
        assert Order.objects.count() == 0

    def test_empty_items(self):
        payload = {"goods": []}
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Order.objects.count() == 0

    def test_zero_quantity(self, good):
        payload = {
            "goods": [{"good_id": good.id, "quantity": 0}],
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Order.objects.count() == 0

    def test_negative_quantity(self, good):
        payload = {
            "goods": [{"good_id": good.id, "quantity": -1}],
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Order.objects.count() == 0

    def test_invalid_good(self):
        payload = {
            "goods": [{"good_id": 99999, "quantity": 1}],
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data

    def test_expired_promo(self, good):
        PromoCode.objects.create(
            code="EXPIRED",
            discount_percent=Decimal("10.00"),
            max_usages=10,
            expires_at=timezone.now() - timedelta(days=1),
        )
        payload = {
            "promo_code": "EXPIRED",
            "goods": [{"good_id": good.id, "quantity": 1}],
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data

    def test_nonexistent_promo(self, good):
        payload = {
            "promo_code": "DOES_NOT_EXIST",
            "goods": [{"good_id": good.id, "quantity": 1}],
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data

    def test_user_cannot_use_same_promo_twice(self, good, promo):
        payload = {
            "promo_code": "SAVE10",
            "goods": [{"good_id": good.id, "quantity": 1}],
        }
        response1 = self.client.post(self.url, payload, format="json")
        assert response1.status_code == status.HTTP_201_CREATED

        response2 = self.client.post(self.url, payload, format="json")
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response2.data

    def test_max_usages_reached(self, good, half_used_promo):
        self.client.post(
            self.url,
            {"promo_code": "HALF", "goods": [{"good_id": good.id, "quantity": 1}]},
            format="json",
        )
        other_user = User.objects.create_user(
            username="other", password="password123",
        )
        from rest_framework.test import APIClient

        other_client = APIClient()
        other_client.force_authenticate(user=other_user)
        response = other_client.post(
            self.url,
            {"promo_code": "HALF", "goods": [{"good_id": good.id, "quantity": 1}]},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data

    def test_promo_with_category_restriction(self, good, other_category, promo):
        promo.categories.add(good.category)

        other_good = Good.objects.create(
            name="T-Shirt",
            category=other_category,
            price=Decimal("50.00"),
            promo_excluded=False,
        )
        payload = {
            "promo_code": "SAVE10",
            "goods": [
                {"good_id": good.id, "quantity": 1},
                {"good_id": other_good.id, "quantity": 1},
            ],
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        expected_discount = (
            good.price * promo.discount_percent / 100
        ).quantize(Decimal("0.01"))
        expected_total = good.price + other_good.price - expected_discount
        data = response.data
        assert Decimal(data["total"]) == expected_total

    def test_promo_excluded_good_skipped(self, category, good, promo):
        excluded = Good.objects.create(
            name="ExcludedItem",
            category=category,
            price=Decimal("200.00"),
            promo_excluded=True,
        )
        payload = {
            "promo_code": "SAVE10",
            "goods": [
                {"good_id": good.id, "quantity": 1},
                {"good_id": excluded.id, "quantity": 1},
            ],
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        expected_discount = (
            good.price * promo.discount_percent / 100
        ).quantize(Decimal("0.01"))
        expected_total = good.price + excluded.price - expected_discount
        data = response.data
        assert Decimal(data["total"]) == expected_total

    def test_promo_not_applicable_all_excluded(self, category, promo):
        excluded = Good.objects.create(
            name="Excluded",
            category=category,
            price=Decimal("100.00"),
            promo_excluded=True,
        )
        payload = {
            "promo_code": "SAVE10",
            "goods": [{"good_id": excluded.id, "quantity": 1}],
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data
