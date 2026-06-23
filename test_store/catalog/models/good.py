from django.db import models

from .category import Category


class Good(models.Model):
    name = models.CharField(
        max_length=255,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="goods",
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    promo_excluded = models.BooleanField(
        default=False,
    )

    class Meta:
        verbose_name = "Good"
        verbose_name_plural = "Goods"
        ordering = ("name",)

    def __str__(self) -> str:
        return f"{self.name} ({self.price})"
