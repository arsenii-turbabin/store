from django.db import models

from .category import Category


class Good(models.Model):
    name = models.CharField(max_length=255)

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="goods",
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    promo_excluded = models.BooleanField(default=False)
