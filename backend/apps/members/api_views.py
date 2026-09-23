

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Member
from .serializers import MemberSerializer


class MemberViewSet(viewsets.ModelViewSet):
    """
    JSON API for members, used by the React frontend.
    Separate from members/views.py, which serves the server-rendered
    HTML pages (Django admin-style list/form/detail).

    Supports:
      GET  /api/members/                 -> list (with filters below)
      GET  /api/members/?is_founder=true -> founders only
      GET  /api/members/?status=active   -> active only
      GET  /api/members/<id>/            -> retrieve one
      POST /api/members/                 -> create
      PUT/PATCH /api/members/<id>/       -> update
      DELETE /api/members/<id>/          -> delete
    """
    queryset = Member.objects.all().order_by('last_name', 'first_name')
    serializer_class = MemberSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_founder', 'status']
    search_fields = ['first_name', 'last_name', 'email']