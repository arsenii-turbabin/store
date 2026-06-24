from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from catalog.models import Category, Good
from promotions.models import PromoCode
from users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testuser",
        password="password123",
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name="Electronics")


@pytest.fixture
def other_category(db):
    return Category.objects.create(name="Clothing")


@pytest.fixture
def good(category):
    return Good.objects.create(
        name="Laptop",
        category=category,
        price=Decimal("1000.00"),
        promo_excluded=False,
    )


@pytest.fixture
def good2(category):
    return Good.objects.create(
        name="Phone",
        category=category,
        price=Decimal("500.00"),
        promo_excluded=False,
    )


@pytest.fixture
def promo(db):
    return PromoCode.objects.create(
        code="SAVE10",
        discount_percent=Decimal("10.00"),
        max_usages=100,
        expires_at=timezone.now() + timedelta(days=30),
    )


@pytest.fixture
def half_used_promo(db):
    """Promo with only 1 usage left before limit."""
    return PromoCode.objects.create(
        code="HALF",
        discount_percent=Decimal("5.00"),
        max_usages=1,
        expires_at=timezone.now() + timedelta(days=30),
    )


@pytest.fixture
def api_client(user):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=user)
    return client
