from django.conf import settings
from django.db import models


class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    promo_code = models.ForeignKey(
        "promotions.PromoCode",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Order #{self.pk}"
