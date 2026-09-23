
from rest_framework.routers import DefaultRouter

from apps.members.api_views import MemberViewSet

router = DefaultRouter()
router.register(r'', MemberViewSet, basename='member-api')

urlpatterns = router.urls