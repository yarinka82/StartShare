from django.db import models
from django.utils.translation import gettext_lazy as _


class Member(models.Model):
    """
    Модель учасника (Member) організації/клубу.
    Віповідає бізнес-вимогам MVP та закладає фундамент для аналітики й CRM.
    """
    STATUS_CHOICES = [
        ('active', 'Активний'),
        ('inactive', 'Неактивний'),
    ]

    first_name = models.CharField(
        max_length=100, 
        verbose_name=_('First Name')
    )
    last_name = models.CharField(
        max_length=100, 
        verbose_name=_('Last Name')
    )
    email = models.EmailField(
        unique=True,
        verbose_name=_('Email Address')
    )
    phone = models.CharField(
        max_length=30, 
        blank=True,
        verbose_name=_('Phone Number')
    )

    join_date = models.DateField(
        verbose_name=_('Join Date')
    )
    
    status = models.CharField('Статус',
        max_length=20, choices=STATUS_CHOICES, default='active')
    
    is_founder = models.BooleanField(
        default=False, 
        verbose_name=_('Is Founder')
    )
    
    # Системні поля для аудиту та відстеження
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name=_('Updated At')
    )
    # дод. поля
    birth_date = models.DateField(
        verbose_name=_('Дата народження'),
        null=True,
        blank=True
    )
    address = models.CharField(
        verbose_name=_('Адреса'),
        max_length=255,
        blank=True
    )
    notes = models.TextField(
        verbose_name=_('Примітки'),
        blank=True
    )
    class Meta:
        verbose_name = _('Member')
        verbose_name_plural = _('Members')
        ordering = ['-join_date', 'last_name', 'first_name']
        indexes = [
            models.Index(fields=['status', 'join_date'],
                         name='idx_member_status_join'),
        ]

    def __str__(self):
        return f"{self.last_name}, {self.first_name} ({self.email})"

