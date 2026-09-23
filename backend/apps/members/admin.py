
from django.contrib import admin
from django.utils.translation import ngettext
from .models import Member

try:
    from apps.payments.models import Payment
    HAS_PAYMENTS = True
except ImportError:
    HAS_PAYMENTS = False


if HAS_PAYMENTS:
    class PaymentInline(admin.TabularInline):
        """
        Shows this member's payment history right on their admin page —
        the "картка члена з історією платежів" from the original spec,
        available for free inside the admin.
        """
        model = Payment
        extra = 0
        fields = ('date', 'type', 'amount', 'status', 'period', 'comment')
        ordering = ('-date',)
        show_change_link = True


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        'last_name', 'first_name', 'email', 'phone',
        'join_date', 'status', 'is_founder',
    )
    list_filter = ('status', 'is_founder', 'join_date')
    search_fields = ('last_name', 'first_name', 'email', 'phone')

    # Toggle status/founder flag directly from the list, no need to open each record
    list_editable = ('status', 'is_founder')

    # Quick year/month/day drill-down above the list — handy once you have
    # more than a couple dozen members
    date_hierarchy = 'join_date'

    list_per_page = 50
    ordering = ('last_name', 'first_name')

    fieldsets = (
        ('Особисті дані', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'birth_date', 'address')
        }),
        ('Членство', {
            'fields': ('join_date', 'status', 'is_founder')
        }),
        ('Примітки', {
            'fields': ('notes',),
            'classes': ('collapse',),  # collapsed by default, rarely needed at a glance
        }),
    )

    if HAS_PAYMENTS:
        inlines = [PaymentInline]

    actions = ['mark_active', 'mark_inactive', 'mark_founder', 'unmark_founder']

    @admin.action(description='Позначити як активних')
    def mark_active(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(
            request,
            ngettext(
                '%d член позначений як активний.',
                '%d членів позначено як активні.',
                updated,
            ) % updated,
        )

    @admin.action(description='Позначити як неактивних')
    def mark_inactive(self, request, queryset):
        updated = queryset.update(status='inactive')
        self.message_user(
            request,
            ngettext(
                '%d член позначений як неактивний.',
                '%d членів позначено як неактивні.',
                updated,
            ) % updated,
        )

    @admin.action(description='Позначити як засновників')
    def mark_founder(self, request, queryset):
        updated = queryset.update(is_founder=True)
        self.message_user(request, f'{updated} члена(ів) позначено як засновників.')

    @admin.action(description='Зняти позначку засновника')
    def unmark_founder(self, request, queryset):
        updated = queryset.update(is_founder=False)
        self.message_user(request, f'Позначку знято у {updated} члена(ів).')
    
    if HAS_PAYMENTS:
        @admin.register(Payment)
        class PaymentAdmin(admin.ModelAdmin):
            list_display = ('date', 'type', 'member', 'source_name', 'amount', 'status', 'period')
            list_filter = ('type', 'status', 'date')
            search_fields = ('member__last_name', 'member__first_name', 'source_name', 'comment')
            date_hierarchy = 'date'
            ordering = ('-date',)
            autocomplete_fields = ('member',)
            list_per_page = 50