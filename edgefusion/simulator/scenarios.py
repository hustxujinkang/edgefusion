from copy import deepcopy
from typing import Any


SCENARIO_TEMPLATES: dict[str, dict[str, Any]] = {
    "sunny_midday": {
        "base_load_w": 1500,
        "pv": {
            "count": 1,
            "available_power_w": 9000,
            "power_limit_w": 9000,
            "min_power_limit_w": 0,
        },
        "storage": {
            "count": 1,
            "soc": 55,
            "max_charge_power_w": 2500,
            "max_discharge_power_w": 2500,
            "initial_mode": "auto",
            "initial_charge_power_w": 2500,
            "initial_discharge_power_w": 2500,
        },
        "chargers": {
            "count": 2,
            "session_active": True,
            "power_w": 2500,
            "max_power_w": 7000,
            "min_power_w": 1000,
        },
    },
    "cloud_pass": {
        "base_load_w": 1800,
        "pv": {
            "count": 1,
            "available_power_w": 9500,
            "power_limit_w": 9500,
            "min_power_limit_w": 0,
        },
        "storage": {
            "count": 1,
            "soc": 60,
            "max_charge_power_w": 2500,
            "max_discharge_power_w": 2500,
            "initial_mode": "auto",
        },
        "chargers": {
            "count": 2,
            "session_active": True,
            "power_w": 2200,
            "max_power_w": 7000,
            "min_power_w": 1000,
        },
    },
    "low_soc": {
        "base_load_w": 2000,
        "pv": {
            "count": 1,
            "available_power_w": 5000,
            "power_limit_w": 5000,
            "min_power_limit_w": 0,
        },
        "storage": {
            "count": 1,
            "soc": 8,
            "max_charge_power_w": 600,
            "max_discharge_power_w": 600,
            "initial_mode": "auto",
            "initial_charge_power_w": 600,
            "initial_discharge_power_w": 600,
        },
        "chargers": {
            "count": 1,
            "session_active": True,
            "power_w": 2000,
            "max_power_w": 5000,
            "min_power_w": 1000,
        },
    },
    "charger_rush": {
        "base_load_w": 5000,
        "pv": {
            "count": 1,
            "available_power_w": 1500,
            "power_limit_w": 1500,
            "min_power_limit_w": 0,
        },
        "storage": {
            "count": 1,
            "soc": 50,
            "max_charge_power_w": 2000,
            "max_discharge_power_w": 2000,
            "initial_mode": "auto",
        },
        "chargers": {
            "count": 3,
            "session_active": True,
            "power_w": 4500,
            "max_power_w": 7000,
            "min_power_w": 1000,
        },
    },
}

DEFAULT_SCENARIO = "sunny_midday"
CLOUD_PASS_RATIOS = (1.0, 0.45, 0.8, 0.35, 0.9, 1.0)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)

    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)

    return merged


def resolve_site_config(config: dict[str, Any] | None) -> dict[str, Any]:
    raw_config = deepcopy(config or {})
    scenario_name = raw_config.get("scenario", DEFAULT_SCENARIO)
    template = deepcopy(SCENARIO_TEMPLATES.get(scenario_name, SCENARIO_TEMPLATES[DEFAULT_SCENARIO]))
    template["scenario"] = scenario_name
    return _deep_merge(template, raw_config)


def apply_scenario_step(site_simulator, step_index: int):
    if site_simulator.config.get("scenario") != "cloud_pass":
        return

    ratio = CLOUD_PASS_RATIOS[step_index % len(CLOUD_PASS_RATIOS)]
    for pv in site_simulator.pvs:
        pv.set_data("available_power", round(pv.max_power * ratio, 2))
