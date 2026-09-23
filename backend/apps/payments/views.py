from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils.dateparse import parse_date
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Payment

from .serializers import PaymentSerializer



class PaymentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    """
    CRUD для платежів/надходжень.
    Підтримує фільтрацію списку через query-параметри:
    ?type=donation&status=paid&member=<id>&date_from=2026-01-01&date_to=2026-12-31
    """

    def _get_queryset(self):
        qs = Payment.objects.select_related('member').all()
        return qs

    def _filter_queryset(self, qs, request):
        params = request.query_params

        payment_type = params.get('type')
        if payment_type:
            qs = qs.filter(type=payment_type)

        payment_status = params.get('status')
        if payment_status:
            qs = qs.filter(status=payment_status)

        member_id = params.get('member')
        if member_id:
            qs = qs.filter(member_id=member_id)

        date_from = parse_date(params.get('date_from', '') or '')
        if date_from:
            qs = qs.filter(date__gte=date_from)

        date_to = parse_date(params.get('date_to', '') or '')
        if date_to:
            qs = qs.filter(date__lte=date_to)

        return qs

    def list(self, request):
        qs = self._filter_queryset(self._get_queryset(), request)
        serializer = PaymentSerializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        payment = self._get_queryset().filter(pk=pk).first()
        if payment is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = PaymentSerializer(payment)
        return Response(serializer.data)

    def update(self, request, pk=None):
        payment = self._get_queryset().filter(pk=pk).first()
        if payment is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = PaymentSerializer(payment, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        payment = self._get_queryset().filter(pk=pk).first()
        if payment is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = PaymentSerializer(payment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        payment = self._get_queryset().filter(pk=pk).first()
        if payment is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        payment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FinancialOverviewView(APIView):
    permission_classes = [IsAuthenticated]
    """
    Сторінка "Фінансовий огляд": загальна сума надходжень за період
    (тільки оплачені), розбивка по типах, по статусу (paid/owed)
    та по періодах (місяцях) — для графіку динаміки.

    GET /api/financial-overview/?date_from=2026-01-01&date_to=2026-12-31
    Без параметрів — за весь час.
    """
    
    def get(self, request):
        base_qs = Payment.objects.all()
        
        date_from = parse_date(request.query_params.get('date_from', '') or '')
        if date_from:
            base_qs = base_qs.filter(date__gte=date_from)
        
        date_to = parse_date(request.query_params.get('date_to', '') or '')
        if date_to:
            base_qs = base_qs.filter(date__lte=date_to)
        
        paid_qs = base_qs.filter(status=Payment.PaymentStatus.PAID)
        owed_qs = base_qs.filter(status=Payment.PaymentStatus.OWED)
        
        total = paid_qs.aggregate(total=Sum('amount'))['total'] or 0
        owed_total = owed_qs.aggregate(total=Sum('amount'))['total'] or 0
        
        # --- розбивка по типах (як і раніше) ---
        paid_by_type = {
            row['type']: row['total']
            for row in paid_qs.values('type').annotate(total=Sum('amount'))
        }
        owed_by_type = {
            row['type']: row['total']
            for row in owed_qs.values('type').annotate(total=Sum('amount'))
        }
        
        breakdown = []
        for value, label in Payment.PaymentType.choices:
            breakdown.append({
                'type': value,
                'type_display': str(label),
                'total': paid_by_type.get(value, 0),
                'owed': owed_by_type.get(value, 0),
            })
        
        # --- НОВЕ: розбивка по періодах (місяцях) ---
        # Групуємо і оплачені, і заборговані суми по місяцю дати платежу,
        # щоб фронт міг намалювати один графік із двома рядами (paid / owed).
        # NB: анотацію не можна назвати "period" — так називається поле моделі Payment.
        paid_by_period = {
            row['month']: row['total']
            for row in (
                paid_qs
                .annotate(month=TruncMonth('date'))
                .values('month')
                .annotate(total=Sum('amount'))
                .order_by('month')
            )
        }
        owed_by_period = {
            row['month']: row['total']
            for row in (
                owed_qs
                .annotate(month=TruncMonth('date'))
                .values('month')
                .annotate(total=Sum('amount'))
                .order_by('month')
            )
        }
        
        all_periods = sorted(set(paid_by_period) | set(owed_by_period))
        by_period = [
            {
                'period': month.strftime('%Y-%m') if month else None,
                'total': paid_by_period.get(month, 0),
                'owed': owed_by_period.get(month, 0),
            }
            for month in all_periods
        ]
        
        return Response({
            'date_from': date_from,
            'date_to': date_to,
            'total': total,
            'owed_total': owed_total,
            'breakdown': breakdown,
            'by_period': by_period,
        })