from django.conf import settings
from django.db import models


class PromoCodeUsage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="promo_code_usages",
    )

    promo_code = models.ForeignKey(
        "promotions.PromoCode",
        on_delete=models.CASCADE,
        related_name="usages",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Promo code usage"
        verbose_name_plural = "Promo code usages"
        ordering = ("-created_at",)

        constraints = [
            models.UniqueConstraint(
                fields=("user", "promo_code"),
                name="unique_user_promo_code_usage",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id} -> {self.promo_code.code}"
