from .models import *
from django.db.models import Sum
def OutstandingBalance(request):
    if request.user.is_authenticated:
        user = request.user

        digitizing_total = DigitizingOrder.objects.filter(
            user=user,
            payment_status="Pending Payment",
            order_status__in=["Delivered", "Edited"]
        ).aggregate(total=Sum("amount"))["total"] or 0

        vector_total = VectorOrder.objects.filter(
            user=user,
            payment_status="Pending Payment",
            order_status__in=["Delivered", "Edited"]
        ).aggregate(total=Sum("amount"))["total"] or 0

        patches_total = PatchesOrder.objects.filter(
            user=user,
            payment_status="Pending Payment",
            order_status__in=["Delivered", "Edited"]
        ).aggregate(total=Sum("amount"))["total"] or 0

        outstanding_balance = digitizing_total + vector_total + patches_total
    else:
        outstanding_balance = 0

    return {
        "outstanding_balance": outstanding_balance
    }

