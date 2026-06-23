from django.db import models


class PromoCode(models.Model):
    code = models.CharField(
        max_length=50,
        unique=True,
    )
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )
    categories = models.ManyToManyField(
        "catalog.Category",
        blank=True,
        related_name="promo_codes",
    )
    max_usages = models.PositiveIntegerField()
    usages_count = models.PositiveIntegerField(
        default=0,
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Promo code"
        verbose_name_plural = "Promo codes"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.code
