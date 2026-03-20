from . import generic, xj
from .generic import GENERIC_POINT_TABLES, GENERIC_VENDOR_PROFILE
from .xj import XJ_POINT_TABLES, XJ_VENDOR_PROFILE

VENDOR_PROFILES = {
    "generic": GENERIC_VENDOR_PROFILE,
    "xj": XJ_VENDOR_PROFILE,
}

VENDOR_POINT_TABLES = {
    key: value.get("tables", {})
    for key, value in VENDOR_PROFILES.items()
}


def _normalize_name(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


VENDOR_ALIASES = {
    alias: vendor_key
    for vendor_key, profile in VENDOR_PROFILES.items()
    for alias in {_normalize_name(vendor_key), *(_normalize_name(item) for item in profile.get("aliases", []))}
    if alias
}


def get_vendor_point_tables(vendor: str) -> dict:
    return VENDOR_POINT_TABLES.get(resolve_vendor_key(vendor) or vendor, {})


def resolve_vendor_key(vendor: str | None) -> str | None:
    normalized = _normalize_name(vendor)
    if not normalized:
        return None
    return VENDOR_ALIASES.get(normalized)


def get_vendor_default_model(vendor: str | None, device_type: str | None) -> str | None:
    vendor_key = resolve_vendor_key(vendor)
    if not vendor_key or not device_type:
        return None
    profile = VENDOR_PROFILES.get(vendor_key, {})
    default_models = profile.get("default_models", {})
    if isinstance(default_models, dict):
        return default_models.get(device_type)
    return None


def resolve_vendor_model(model: str | None, vendor: str | None = None, device_type: str | None = None) -> str | None:
    normalized_model = _normalize_name(model)
    vendor_key = resolve_vendor_key(vendor)
    candidate_vendors = [vendor_key] if vendor_key else list(VENDOR_POINT_TABLES.keys())

    if normalized_model:
        for current_vendor in candidate_vendors:
            tables = VENDOR_POINT_TABLES.get(current_vendor, {})
            for model_key, table in tables.items():
                if device_type and table.get("device_type") != device_type:
                    continue
                aliases = {
                    _normalize_name(model_key),
                    _normalize_name(table.get("name")),
                    *(_normalize_name(item) for item in table.get("model_aliases", [])),
                }
                aliases.discard("")
                if normalized_model in aliases:
                    return model_key

    if vendor_key:
        return get_vendor_default_model(vendor_key, device_type)
    return None


def get_vendor_point_tables_for_device_type(device_type: str) -> dict:
    return {
        key: value
        for tables in VENDOR_POINT_TABLES.values()
        for key, value in tables.items()
        if value.get("device_type") == device_type
    }


__all__ = [
    "generic",
    "xj",
    "GENERIC_POINT_TABLES",
    "GENERIC_VENDOR_PROFILE",
    "XJ_POINT_TABLES",
    "XJ_VENDOR_PROFILE",
    "VENDOR_PROFILES",
    "VENDOR_POINT_TABLES",
    "VENDOR_ALIASES",
    "get_vendor_point_tables",
    "get_vendor_point_tables_for_device_type",
    "get_vendor_default_model",
    "resolve_vendor_key",
    "resolve_vendor_model",
]
