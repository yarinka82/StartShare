from rest_framework import serializers

from common.models import Sector, Stage, Region, BusinessModel
from .models import InvestorMandate

# NOTE: custom messages are stable error codes, the frontend translates them.


def _choice_list(choices, *, required_values: bool):
    kwargs = {"child": serializers.ChoiceField(choices=choices.choices)}
    if required_values:
        return serializers.ListField(allow_empty=False, error_messages={"empty": "mandate_list_required"}, **kwargs)
    return serializers.ListField(allow_empty=True, required=False, default=list, **kwargs)


def _canonical(choices, values):
    """Remove duplicates and use the order of the list, so equal selections are stored equally."""
    wanted = set(values)
    return [value for value, _ in choices.choices if value in wanted]


def _validate_and_canonicalize(model_cls, values: list[str], required: bool = True) -> list[str]:
    if not values:
        if required:
            raise serializers.ValidationError("mandate_list_required")
        return []

    valid_codes = list(model_cls.objects.filter(is_active=True).values_list("code", flat=True))
    valid_set = set(valid_codes)

    invalid = [v for v in values if v not in valid_set]
    if invalid:
        # Важливо: тест очікує підрядок "not a valid choice"
        raise serializers.ValidationError(f"'{invalid[0]}' is not a valid choice.")

    return [code for code in valid_codes if code in values]


class MandateSerializer(serializers.Serializer):
    """Серіалізатор інвестиційного мандату."""

    sectors = serializers.ListField(
        child=serializers.CharField(max_length=32),
        allow_empty=False,
        error_messages={"empty": "mandate_list_required", "required": "mandate_list_required"}
    )
    stages = serializers.ListField(
        child=serializers.CharField(max_length=32),
        allow_empty=False,
        error_messages={"empty": "mandate_list_required", "required": "mandate_list_required"}
    )
    regions = serializers.ListField(
        child=serializers.CharField(max_length=32),
        allow_empty=False,
        error_messages={"empty": "mandate_list_required", "required": "mandate_list_required"}
    )
    business_models = serializers.ListField(
        child=serializers.CharField(max_length=32),
        allow_empty=True,
        required=False,
        default=list,
    )
    ticket_min = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=1, max_value=1_000_000_000
    )
    ticket_max = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=1, max_value=1_000_000_000
    )

    def validate_sectors(self, v):
        return _validate_and_canonicalize(Sector, v, required=True)

    def validate_stages(self, v):
        return _validate_and_canonicalize(Stage, v, required=True)

    def validate_regions(self, v):
        return _validate_and_canonicalize(Region, v, required=True)

    def validate_business_models(self, v):
        return _validate_and_canonicalize(BusinessModel, v, required=False)

    def validate(self, attrs):
        if attrs.get("ticket_max") and attrs.get("ticket_min") and attrs["ticket_max"] < attrs["ticket_min"]:
            raise serializers.ValidationError({"ticket_max": "ticket_max_below_min"})
        return attrs



class MandateOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestorMandate
        fields = ("sectors", "stages", "regions", "business_models", "ticket_min", "ticket_max", "updated_at")
        read_only_fields = fields


class ConfirmStatusSerializer(serializers.Serializer):
    accept = serializers.BooleanField()

    def validate_accept(self, value):
        if value is not True:
            raise serializers.ValidationError("status_confirmation_required")
        return value
