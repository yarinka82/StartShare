from django.contrib.auth.password_validation import validate_password as run_password_validators
from rest_framework import serializers

from .models import Role


# NOTE: custom validation messages are stable error codes (e.g. "accept_agb_required").
# The frontend maps them to translated texts.


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    role = serializers.ChoiceField(choices=Role.choices)
    accept_agb = serializers.BooleanField()
    accept_datenschutz = serializers.BooleanField()

    def validate_email(self, value):
        return value.strip().lower()

    def validate_password(self, value):
        run_password_validators(value)
        return value

    def validate_accept_agb(self, value):
        if value is not True:
            raise serializers.ValidationError("accept_agb_required")
        return value

    def validate_accept_datenschutz(self, value):
        if value is not True:
            raise serializers.ValidationError("accept_datenschutz_required")
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False)

    def validate_email(self, value):
        return value.strip().lower()


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(trim_whitespace=False, max_length=128)


class MeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    role = serializers.CharField()
    email_verified = serializers.BooleanField(source="is_email_verified")
