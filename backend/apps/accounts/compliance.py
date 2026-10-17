from __future__ import annotations

import warnings
from datetime import date

from django.conf import settings

from apps.accounts.models import VendorCompliance


class VendorComplianceError(RuntimeError):
    """Raised when an external vendor is not allowed to process data."""


class ProviderBlocked(VendorComplianceError):
    """Raised when a provider is not eligible to process data at runtime."""


def _normalize_region(value: str | None) -> str:
    return (value or "").strip().lower()


def is_ai_notice_enabled() -> bool:
    """Single source of truth for showing the AI disclosure text G."""
    provider = VendorCompliance.objects.filter(provider_name="azure_openai").first()
    if provider is None:
        provider = VendorCompliance.objects.filter(name="azure_openai").first()
    if provider is None:
        return False
    if not provider.dpa_signed:
        return False
    if provider.dpa_valid_until and provider.dpa_valid_until < date.today():
        return False
    if _normalize_region(provider.region) not in { _normalize_region(v) for v in getattr(settings, "ALLOWED_REGIONS", ["eu"]) }:
        return False
    return bool(provider.no_model_training)


def get_deprecated_teaser_avv_flag() -> bool:
    """Backwards compatibility alias. Use VendorCompliance as source of truth."""
    if hasattr(settings, "TEASER_AVV_SIGNED"):
        warnings.warn(
            "TEASER_AVV_SIGNED is deprecated; use VendorCompliance records for azure_openai.",
            DeprecationWarning,
            stacklevel=2,
        )
        return bool(getattr(settings, "TEASER_AVV_SIGNED", False))
    return False


def assert_provider_allowed(provider_name: str) -> None:
    """Runtime gate: only approved EU providers may process personal/business data."""
    allowed_regions = {_normalize_region(v) for v in getattr(settings, "ALLOWED_REGIONS", ["eu"]) }

    provider = VendorCompliance.objects.filter(provider_name=provider_name).first()
    if provider is None:
        provider = VendorCompliance.objects.filter(name=provider_name).first()
    if provider is None:
        raise ProviderBlocked(f"Provider '{provider_name}' is not registered in VendorCompliance.")

    if not provider.dpa_signed:
        raise ProviderBlocked(f"Provider '{provider_name}' is blocked: DPA/AVV is not signed.")

    if provider.dpa_valid_until and provider.dpa_valid_until < date.today():
        raise ProviderBlocked(f"Provider '{provider_name}' is blocked: DPA/AVV expired on {provider.dpa_valid_until}.")

    if _normalize_region(provider.region) not in allowed_regions:
        raise ProviderBlocked(
            f"Provider '{provider_name}' is blocked: region '{provider.region}' is not in ALLOWED_REGIONS."
        )

    provider_type = (provider.provider_type or provider.vendor_type or "").lower()
    if provider_type in {"ai", "llm"} and provider.no_model_training is not True:
        raise ProviderBlocked(
            f"Provider '{provider_name}' is blocked: no_model_training must be True for AI/LLM providers."
        )


def vendor_allowed(vendor_key: str, data_category: str, *, vendor_type: str | None = None) -> bool:
    """Returns True when a configured external provider is approved for the given data type.

    This is intentionally fail-closed: until a real provider contract is signed and recorded,
    all external processing is blocked.
    """
    provider = VendorCompliance.objects.filter(provider_name=vendor_key).first()
    if provider is None:
        provider = VendorCompliance.objects.filter(name=vendor_key).first()

    if provider is not None:
        try:
            assert_provider_allowed(vendor_key)
        except ProviderBlocked:
            return False
    else:
        providers = getattr(settings, "EXTERNAL_PROVIDER_CONFIGS", {})
        config = providers.get(vendor_key)
        if config is None:
            return False
        if config.get("enabled", False) is not True:
            return False
        if not config.get("dpa_signed", False):
            return False
        valid_until = config.get("dpa_valid_until")
        if valid_until:
            try:
                if date.fromisoformat(valid_until) < date.today():
                    return False
            except ValueError:
                return False
        allowed = config.get("allowed_data_types", [])
        if allowed and data_category not in allowed:
            return False
        if data_category == "ai_prompt" and config.get("no_model_training") is not True:
            return False
        if vendor_type == "ai" and config.get("no_model_training") is not True:
            return False

    return True


def ensure_vendor_allowed(vendor_key: str, data_category: str, *, vendor_type: str | None = None) -> None:
    if not vendor_allowed(vendor_key, data_category, vendor_type=vendor_type):
        raise VendorComplianceError(
            f"Vendor '{vendor_key}' is not approved for '{data_category}'. "
            "A valid AVV/DPA and compliance configuration must exist before external processing."
        )
