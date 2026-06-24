from django.contrib import admin

from promotions.models import PromoCode, PromoCodeUsage


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "code",
        "discount_percent",
        "max_usages",
        "usages_count",
        "expires_at",
    )

    search_fields = ("code",)

    filter_horizontal = (
        "categories",
    )


@admin.register(PromoCodeUsage)
class PromoCodeUsageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "promo_code",
        "order",
        "created_at",
    )

    search_fields = (
        "user__username",
        "promo_code__code",
    )

    list_filter = (
        "promo_code",
    )
