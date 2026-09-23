from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Member
from .forms import MemberForm
from .serializers import MemberSerializer


class MemberViewSet(viewsets.ModelViewSet):
    """
    JSON API for members, used by the React frontend.
    Separate from members/views.py, which serves the server-rendered
    HTML pages (Django admin-style list/form/detail).
    Requires an authenticated session (see apps.accounts for login/logout).

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
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_founder', 'status']
    search_fields = ['first_name', 'last_name', 'email']
    
    
class MemberListView(ListView):
    model = Member
    template_name = 'members/member_list.html'
    context_object_name = 'members'

    def get_queryset(self):
        queryset = super().get_queryset()
        is_founder = self.request.GET.get('is_founder')
        if is_founder == 'true':
            queryset = queryset.filter(is_founder=True)
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset


class MemberDetailView(DetailView):
    model = Member
    template_name = 'members/member_detail.html'
    context_object_name = 'member'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Payment history requires payments app; wire this up once that model exists:
        # context['payments'] = self.object.payments.all().order_by('-date')
        return context


def member_create(request):
    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('member-list')
    else:
        form = MemberForm()
    return render(request, 'members/member_form.html', {'form': form, 'title': 'Додати члена'})


def member_edit(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            return redirect('member-detail', pk=member.pk)
    else:
        form = MemberForm(instance=member)
    return render(request, 'members/member_form.html', {'form': form, 'title': 'Редагувати члена'})


def home_view(request):
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CRM System</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            .container { max-width: 600px; margin: 0 auto; }
            .links { margin-top: 30px; }
            .links a { display: inline-block; margin: 10px; padding: 12px 24px;
                       background: #007bff; color: white; text-decoration: none;
                       border-radius: 5px; }
            .links a:hover { background: #0056b3; }
            .status { color: green; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏢 CRM System</h1>
            <p class="status">✅ Сервер работает успешно!</p>
            <p>Версия: Django 6.1</p>
            <div class="links">
                <a href="/admin/">🔐 Войти в админку</a>
                <a href="/admin/">📊 Административная панель</a>
            </div>
            <p style="margin-top: 30px; color: #666; font-size: 14px;">
                API доступен по адресу: /api/
            </p>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)