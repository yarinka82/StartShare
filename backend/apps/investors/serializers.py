from rest_framework import serializers

from common.models import BusinessModel, Country, Region, Sector, Stage
from .models import Mandate


def _validate_and_canonicalize(model_cls, values: list[str], required: bool = True) -> list[str]:
    """
    Проверяет валидность кодов по справочнику (is_active=True)
    и возвращает их в каноническом порядке без дубликатов.
    """
    if not values:
        if required:
            raise serializers.ValidationError("mandate_list_required")
        return []

    valid_codes = list(model_cls.objects.filter(is_active=True).values_list("code", flat=True))
    valid_set = set(valid_codes)

    invalid = [v for v in values if v not in valid_set]
    if invalid:
        # Важно: тесты часто ожидают подстроку "not a valid choice"
        raise serializers.ValidationError(f"'{invalid[0]}' is not a valid choice.")

    # Возвращаем в стабильном порядке справочника, исключая дубликаты
    return [code for code in valid_codes if code in values]



class MandateSerializer(serializers.Serializer):
    """Сериализатор входных данных для создания/обновления версии мандата."""

    # Обязательные критерии (Hard filters)
    sector_codes = serializers.ListField(
        child=serializers.CharField(max_length=32),
        allow_empty=False,
        error_messages={"empty": "mandate_list_required", "required": "mandate_list_required"},
    )
    stage_codes = serializers.ListField(
        child=serializers.CharField(max_length=32),
        allow_empty=False,
        error_messages={"empty": "mandate_list_required", "required": "mandate_list_required"},
    )
    country_codes = serializers.ListField(
        child=serializers.CharField(max_length=2),
        allow_empty=False,
        error_messages={"empty": "mandate_list_required", "required": "mandate_list_required"},
    )

    # Опциональные критерии (Soft filters)
    region_codes = serializers.ListField(
        child=serializers.CharField(max_length=6),
        allow_empty=True,
        required=False,
        default=list,
    )
    business_model_codes = serializers.ListField(
        child=serializers.CharField(max_length=32),
        allow_empty=True,
        required=False,
        default=list,
    )

    # Финансовые чеки (EUR)
    check_min_eur = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=1, max_value=1_000_000_000
    )
    check_max_eur = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=1, max_value=1_000_000_000
    )

    def validate_sector_codes(self, v):
        return _validate_and_canonicalize(Sector, v, required=True)

    def validate_stage_codes(self, v):
        return _validate_and_canonicalize(Stage, v, required=True)

    def validate_country_codes(self, v):
        return _validate_and_canonicalize(Country, v, required=True)

    def validate_region_codes(self, v):
        return _validate_and_canonicalize(Region, v, required=False)

    def validate_business_model_codes(self, v):
        return _validate_and_canonicalize(BusinessModel, v, required=False)

    def validate(self, attrs):
        min_val = attrs.get("check_min_eur")
        max_val = attrs.get("check_max_eur")
        if min_val and max_val and max_val < min_val:
            raise serializers.ValidationError({"check_max_eur": "ticket_max_below_min"})
        return attrs



class MandateOutSerializer(serializers.ModelSerializer):
    """Сериализатор для отдачи данных мандата клиенту."""

    class Meta:
        model = Mandate
        fields = (
            "version",
            "is_current",
            "sector_codes",
            "stage_codes",
            "country_codes",
            "region_codes",
            "business_model_codes",
            "check_min_eur",
            "check_max_eur",
            "source",
            "created_at",
        )
        read_only_fields = fields



class ConfirmStatusSerializer(serializers.Serializer):
    """Подтверждение статуса инвестора (согласие)."""

    accept = serializers.BooleanField()

    def validate_accept(self, value):
        if value is not True:
            raise serializers.ValidationError("status_confirmation_required")
        return value
