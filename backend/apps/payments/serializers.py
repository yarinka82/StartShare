from decimal import Decimal
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import Payment



class PaymentSerializer(serializers.ModelSerializer):
    member_name = serializers.SerializerMethodField()
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'member', 'member_name', 'amount', 'date', 'type', 'type_display',
            'source_name', 'period', 'status', 'status_display', 'comment', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        # merge with existing instance data on PATCH so validation sees the full picture
        payment_type = attrs.get('type', getattr(self.instance, 'type', None))
        member = attrs.get('member', getattr(self.instance, 'member', None))
        source_name = attrs.get('source_name', getattr(self.instance, 'source_name', ''))

        if payment_type == Payment.PaymentType.MEMBERSHIP_FEE:
            if member is None:
                raise serializers.ValidationError({
                    'member': _('Членський внесок має бути прив’язаний до члена організації.')
                })
        else:
            if member is not None:
                raise serializers.ValidationError({
                    'member': _('Пожертва/спонсорство/грант не прив’язуються до конкретного члена.')
                })
            if not source_name:
                raise serializers.ValidationError({
                    'source_name': _('Вкажіть назву джерела (фонд, спонсор тощо).')
                })

        amount = attrs.get('amount', getattr(self.instance, 'amount', None))
        if amount is not None and amount <= Decimal('0'):
            raise serializers.ValidationError({'amount': _('Сума має бути більшою за нуль.')})

        return attrs
    
    def get_member_name(self, obj):
        if obj.member is not None:
            return f"{obj.member.last_name} {obj.member.first_name}"
            # или: return str(obj.member)
        return None