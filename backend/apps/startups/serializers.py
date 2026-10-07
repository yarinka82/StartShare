
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from common.models import Sector, Stage, BusinessModel, Country
from apps.startups.models import StartupProfile, StartupPrivateDetails


REQUIRED_FOR_COMPLETE = ("sector", "stage", "country", "amount_sought", "team_size")


STATUS_TRANSITIONS = {
    "LIVE": {"PAUSED", "REMOVED"},
    "PAUSED": {"LIVE", "REMOVED"},
    "DRAFT": {"REMOVED"},
}


class StartupProfileSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    # Довідники
    sector = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Sector.objects.all(),
        required=False,
        allow_null=True,
    )
    stage = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Stage.objects.all(),
        required=False,
        allow_null=True,
    )
    business_model = serializers.SlugRelatedField(
        slug_field="code",
        queryset=BusinessModel.objects.all(),
        required=False,
        allow_null=True,
    )
    country = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Country.objects.all(),
        required=False,
        allow_null=True,
    )

    round_amount_eur = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("1"),
        required=False,
        allow_null=True,
    )
    amount_sought = serializers.DecimalField(
        source="round_amount_eur",
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("1"),
        required=False,
        allow_null=True,
        write_only=True,
    )

    mrr_eur = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
    )
    mrr = serializers.DecimalField(
        source="mrr_eur",
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
        write_only=True,
    )

    growth_pct = serializers.DecimalField(
        max_digits=7,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    growth_percent = serializers.DecimalField(
        source="growth_pct",
        max_digits=7,
        decimal_places=2,
        required=False,
        allow_null=True,
        write_only=True,
    )
    growth_period = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        write_only=True,
    )

    team_size = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True,
    )

    missing_fields = serializers.SerializerMethodField()
    is_complete = serializers.SerializerMethodField()

    class Meta:
        model = StartupProfile
        fields = [
            "public_id",
            "status",
            "company_name",
            "sector",
            "sector_other_text",
            "stage",
            "business_model",
            "business_model_other_text",
            "country",
            "round_amount_eur",
            "amount_sought",
            "mrr_eur",
            "mrr",
            "growth_pct",
            "growth_percent",
            "growth_period",
            "team_size",
            "missing_fields",
            "is_complete",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "public_id",
            "status",
            "missing_fields",
            "is_complete",
            "created_at",
            "updated_at",
        ]

    def to_internal_value(self, data):
        # Дозволяємо очищати поля передачею порожнього рядка: {"sector": ""} -> None
        data = data.copy()
        for field in ["sector", "stage", "business_model", "country"]:
            if field in data and data[field] == "":
                data[field] = None
        return super().to_internal_value(data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Перетворюємо null у "" для консистентності з фронтендом і тестами
        for field in ["sector", "stage", "business_model", "country"]:
            if data.get(field) is None:
                data[field] = ""

        if hasattr(instance, "private_details") and instance.private_details:
            data["company_name"] = instance.private_details.company_name
        else:
            data["company_name"] = ""
        return data

    def validate_country(self, value):
        if value and not value.is_active:
            raise serializers.ValidationError("This country is currently inactive.")
        return value

    def validate_sector(self, value):
        if value and not value.is_active:
            raise serializers.ValidationError("This sector is currently inactive.")
        return value

    def validate_stage(self, value):
        if value and not value.is_active:
            raise serializers.ValidationError("This stage is currently inactive.")
        return value

    def validate_business_model(self, value):
        if value and not value.is_active:
            raise serializers.ValidationError("This business model is currently inactive.")
        return value

    def validate(self, attrs):
        growth = attrs.get("growth_pct")
        period = attrs.get("growth_period")
        if growth is not None and not period:
            raise serializers.ValidationError(
                {"growth_period": "growth_period is required when growth_percent is provided."}
            )
        return attrs
    
    def get_missing_fields(self, obj) -> list[str]:
        missing = []
        
        # 1. Обов'язкові довідники
        for field in ["sector", "stage", "country"]:
            try:
                val = getattr(obj, field)
            except ObjectDoesNotExist:
                val = None
            
            if not val or not getattr(val, "is_active", True):
                missing.append(field)
        
        # 2. М'який критерій business_model
        if getattr(obj, "business_model_id", None):
            try:
                bm = obj.business_model
                if not bm or not bm.is_active:
                    missing.append("business_model")
            except ObjectDoesNotExist:
                missing.append("business_model")
        
        # 3. Сума раунду
        if not obj.round_amount_eur or obj.round_amount_eur <= 0:
            missing.append("amount_sought")
        
        # 4. Розмір команди
        if not obj.team_size or obj.team_size < 1:
            missing.append("team_size")
        
        # 5. Надійна перевірка наявності Deck
        has_deck = False
        try:
            from apps.documents.models import Deck
            # Перевіряємо через користувача, прямий ForeignKey та зворотні зв'язки
            has_deck = (
                    Deck.objects.filter(user=obj.user).exists()
                    or (hasattr(Deck, "startup") and Deck.objects.filter(startup=obj).exists())
                    or (hasattr(Deck, "startup_profile") and Deck.objects.filter(startup_profile=obj).exists())
            )
        except Exception:
            pass
        
        if not has_deck:
            for rel in ["decks", "pitch_decks", "deck_set", "pitchdeck_set", "deck"]:
                if hasattr(obj, rel):
                    val = getattr(obj, rel)
                    if hasattr(val, "exists") and val.exists():
                        has_deck = True
                        break
                    elif getattr(val, "pk", None) or getattr(val, "id", None):
                        has_deck = True
                        break
        
        if not has_deck:
            missing.append("deck")
        
        return missing

    def get_is_complete(self, obj) -> bool:
        return len(self.get_missing_fields(obj)) == 0

    def update(self, instance, validated_data):
        company_name = validated_data.pop("company_name", None)
        validated_data.pop("growth_period", None)

        if company_name is not None:
            details, _ = StartupPrivateDetails.objects.get_or_create(startup_profile=instance)
            details.company_name = company_name
            details.save()

        return super().update(instance, validated_data)