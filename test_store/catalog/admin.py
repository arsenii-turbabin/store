from django.contrib import admin

from catalog.models import Category, Good


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Good)
class GoodAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "category",
        "price",
        "promo_excluded",
    )

    list_filter = (
        "category",
        "promo_excluded",
    )

    search_fields = ("name",)
    ordering = ("name",)
