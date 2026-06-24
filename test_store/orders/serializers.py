from decimal import Decimal

from rest_framework import serializers

from .models import Order, OrderItem


class OrderItemDataSerializer(serializers.Serializer):
    """Serializer for order item input data."""
    good_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)


class CreateOrderInputSerializer(serializers.Serializer):
    """Serializer for POST /api/orders/ request body."""
    promo_code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
    )
    goods = OrderItemDataSerializer(many=True)

    def validate_goods(self, value):
        if not value:
            raise serializers.ValidationError(
                "Order must contain at least one item",
            )
        return value


class GoodItemOutputSerializer(serializers.Serializer):
    """Serializer for a good in the order response."""
    good_id = serializers.IntegerField()
    quantity = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount = serializers.SerializerMethodField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2)

    def get_discount(self, obj: OrderItem) -> str:
        """Return discount as percentage string, e.g. "0.1" for 10%."""
        if obj.order.promo_code_id is None:
            return "0"
        percent = obj.order.promo_code.discount_percent
        return str(percent / Decimal("100"))


class CreateOrderOutputSerializer(serializers.ModelSerializer):
    """Serializer for POST /api/orders/ response."""
    order_id = serializers.IntegerField(source="id", read_only=True)
    goods = GoodItemOutputSerializer(source="items", many=True, read_only=True)
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount = serializers.SerializerMethodField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        model = Order
        fields = (
            "order_id",
            "user_id",
            "goods",
            "price",
            "discount",
            "total",
        )

    def get_discount(self, obj: Order) -> str:
        """Return discount as percentage string, e.g. "0.1" for 10%."""
        if obj.promo_code_id is None:
            return "0"
        return str(obj.promo_code.discount_percent / Decimal("100"))
