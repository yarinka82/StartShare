from rest_framework import serializers

from django.conf import settings
from .models import Country, Deck, StartupProfile
from .validators import validate_deck_file
from ..documents.serializers import DeckSerializer

REQUIRED_FOR_COMPLETE = ("sector", "stage", "country", "amount_sought", "team_size")


class DictionaryItemSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()


STATUS_TRANSITIONS = {
    "LIVE": {"PAUSED", "REMOVED"},
    "PAUSED": {"LIVE", "REMOVED"},
    "DRAFT": {"REMOVED"},
}



class StartupProfileSerializer(serializers.ModelSerializer):
    # sector / stage / business_model are model choices: DRF builds a ChoiceField from them
    # (value = code, "" = not chosen). Country is a DB list, addressed by its code too.
    country = serializers.SlugRelatedField(
        slug_field="code", queryset=Country.objects.filter(is_active=True), allow_null=True, required=False
    )
    amount_sought = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=1, max_value=1_000_000_000,
        allow_null=True, required=False,
    )
    mrr = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=0, max_value=1_000_000_000,
        allow_null=True, required=False,
    )
    growth_percent = serializers.DecimalField(
        max_digits=7, decimal_places=2, min_value=-100, max_value=10000,
        allow_null=True, required=False,
    )
    team_size = serializers.IntegerField(min_value=1, max_value=100000, allow_null=True, required=False)
    deck = serializers.SerializerMethodField()
    is_complete = serializers.SerializerMethodField()
    missing_fields = serializers.SerializerMethodField()
    
    class Meta:
        model = StartupProfile
        fields = (
            "company_name", "sector", "stage", "business_model", "country", "amount_sought", "mrr",
            "growth_percent", "growth_period", "team_size",
            "status", "deck", "is_complete", "missing_fields",
        )
    
    def validate_status(self, value):
        current = self.instance.status if self.instance else None
        if value == current:
            return value
        if value not in STATUS_TRANSITIONS.get(current, set()):
            raise serializers.ValidationError("status_transition_not_allowed")
        return value
    
    def validate(self, attrs):
        percent = attrs.get("growth_percent", getattr(self.instance, "growth_percent", None))
        period = attrs.get("growth_period", getattr(self.instance, "growth_period", ""))
        if percent is not None and not period:
            raise serializers.ValidationError({"growth_period": "growth_period_required"})
        return attrs
    
    def to_internal_value(self, data):
        # Якщо передали країну (наприклад "CH" або "DE"), автоматично робимо її "ch", "de"
        if isinstance(data, dict) and "country" in data and isinstance(data["country"], str):
            data = data.copy()
            data["country"] = data["country"].lower()
        return super().to_internal_value(data)
    
    def get_deck(self, obj):
        deck = getattr(obj, "deck", None)
        return DeckSerializer(deck).data if deck else None

    def get_missing_fields(self, obj):
        def is_missing(field):
            value = getattr(obj, field)
            if value in (None, ""):
                return True
            choices = obj._meta.get_field(field).choices
            if choices:  # a value that is no longer in the approved list counts as not chosen
                return value not in dict(choices)
            return getattr(value, "is_active", True) is False

        missing = [f for f in REQUIRED_FOR_COMPLETE if is_missing(f)]
        if getattr(obj, "deck", None) is None:
            missing.append("deck")
        return missing

    def get_is_complete(self, obj):
        return not self.get_missing_fields(obj)

