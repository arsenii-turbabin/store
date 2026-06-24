from django.db import models


class OrderItem(models.Model):
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="items",
    )
    good = models.ForeignKey(
        "catalog.Good",
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField()
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

    class Meta:
        verbose_name = "Order item"
        verbose_name_plural = "Order items"

    def __str__(self) -> str:
        return f"{self.good.name} x {self.quantity}"
