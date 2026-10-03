from rest_framework import serializers

from apps.profiles.choices import BusinessModel, Region, Sector, Stage

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


class MandateSerializer(serializers.Serializer):
    """Whole mandate in one request (the page has an explicit Save button, no autosave)."""

    sectors = _choice_list(Sector, required_values=True)
    stages = _choice_list(Stage, required_values=True)
    regions = _choice_list(Region, required_values=True)
    business_models = _choice_list(BusinessModel, required_values=False)
    ticket_min = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=1, max_value=1_000_000_000)
    ticket_max = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=1, max_value=1_000_000_000)

    def validate_sectors(self, v):
        return _canonical(Sector, v)

    def validate_stages(self, v):
        return _canonical(Stage, v)

    def validate_regions(self, v):
        return _canonical(Region, v)

    def validate_business_models(self, v):
        return _canonical(BusinessModel, v)

    def validate(self, attrs):
        if attrs["ticket_max"] < attrs["ticket_min"]:
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
