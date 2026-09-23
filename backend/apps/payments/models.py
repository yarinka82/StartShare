from django.db import models
from apps.members.models import Member
from django.utils.translation import gettext_lazy as _


class Payment(models.Model):
    """
    Модель платежів (Payment) для обліку надходжень.
    Відповідає структурі, визначеній у ТЗ (Частина В).
    """
    
    class PaymentType(models.TextChoices):
        """
        Джерела надходжень — система має бути готова обліковувати всі
        чотири з самого початку, навіть якщо зараз активний лише
        membership_fee.
        """
        MEMBERSHIP_FEE = 'membership_fee', _('Членський внесок')  # Mitgliedsbeiträge
        DONATION = 'donation', _('Пожертва')  # Spenden
        SPONSORSHIP = 'sponsorship', _('Спонсорська підтримка')  # Sponsoring
        GRANT = 'grant', _('Грант')  # Fördergelder
    
    class PaymentStatus(models.TextChoices):
        """Як у ТЗ: двостановий статус, а не стан платіжного шлюзу."""
        PAID = 'paid', _('Оплачено')
        OWED = 'owed', _('Заборговано')
    
    member = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,  # preserve payment history if a member is deleted
        related_name='payments',
        null=True,
        blank=True,  # empty when this is a donation/sponsorship/grant,
        verbose_name=_('Член'),  # not tied to a specific member
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Сума'),
    )
    date = models.DateField(
        db_index=True,
        verbose_name=_('Дата'),
    )
    type = models.CharField(
        max_length=50,
        choices=PaymentType.choices,
        db_index=True,
        verbose_name=_('Тип надходження'),
    )
    source_name = models.CharField(
        max_length=100,
        blank=True,
        # For donations/sponsorship/grants: the sponsor's or fund's name.
        # Null/blank for regular membership fees.
        verbose_name=_('Назва джерела'),
    )
    period = models.CharField(
        max_length=50,
        blank=True,
        # e.g. "2026", "2026-Q1" — the billing period a membership fee covers
        verbose_name=_('Період'),
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PAID,
        db_index=True,
        verbose_name=_('Статус'),
    )
    comment = models.TextField(
        blank=True,
        # For grants: can hold the grant agreement number
        verbose_name=_('Коментар'),
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Створено'),
    )
    
    class Meta:
        verbose_name = _('Платіж')
        verbose_name_plural = _('Платежі')
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['date', 'status'], name='idx_payment_date_status'),
            models.Index(fields=['type', 'date'], name='idx_payment_type_date'),
        ]
    
    def __str__(self):
        who = self.member if self.member else (self.source_name or self.get_type_display())
        return f"{who} — {self.amount} EUR ({self.date})"