from django.db import models


class Category(models.Model):
    name = models.CharField(
        verbose_name="Name",
        max_length=255,
        unique=True,
    )

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name
