from django.urls import path
from .views import PaymentViewSet, FinancialOverviewView

urlpatterns = [
    
    path('', PaymentViewSet.as_view({
        'get': 'list',
        'post': 'create',
    })),
    path('<int:pk>/', PaymentViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy',
    })),
    
    # Nested under the same 'api/payments/' prefix set in the main urls.py,
    # so the real address is /api/payments/financial-overview/
    path('financial-overview/', FinancialOverviewView.as_view()),
]