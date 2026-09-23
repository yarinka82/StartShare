from rest_framework import serializers
from .models import Member


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'phone',
            'join_date',
            'status',
            'is_founder',
            'birth_date',
            'address',
            'notes',
        ]
        