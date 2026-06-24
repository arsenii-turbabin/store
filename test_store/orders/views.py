from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.exceptions import OrderError
from orders.serializers import (CreateOrderInputSerializer,
                                CreateOrderOutputSerializer)
from orders.services import OrderService
from promotions.exceptions import PromoError


class CreateOrderView(APIView):
    """POST /api/orders/ — create a new order."""

    permission_classes = (IsAuthenticated,)

    def post(self, request: Request) -> Response:
        serializer = CreateOrderInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        items_data = [
            OrderService.CreateOrderItemData(
                good_id=item["good_id"],
                quantity=item["quantity"],
            )
            for item in serializer.validated_data["goods"]
        ]

        try:
            order = OrderService.create_order(
                user=request.user,
                items=items_data,
                promo_code=serializer.validated_data.get("promo_code"),
            )
        except (OrderError, PromoError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        output_serializer = CreateOrderOutputSerializer(order)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )
