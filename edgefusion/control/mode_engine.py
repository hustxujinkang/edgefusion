from dataclasses import dataclass
from typing import Any

from .site_state import SiteState


@dataclass
class ModeDecision:
    mode: str
    reason: str


def arbitrate_mode(state: SiteState, config: dict[str, Any] | None = None) -> ModeDecision:
    config = config or {}

    if state.manual_override:
        return ModeDecision(mode="manual_override", reason="manual_override_enabled")

    if not state.trusted:
        return ModeDecision(mode="safe_hold", reason="untrusted_site_state")

    if not bool(config.get("export_protect_enabled", True)):
        return ModeDecision(mode="business_normal", reason="export_protect_disabled")

    export_limit_w = float(config.get("export_limit_w", 0))
    export_enter_ratio = float(config.get("export_enter_ratio", 1.0))
    export_threshold_w = -export_limit_w * export_enter_ratio

    if state.grid_power_w is not None and state.grid_power_w <= export_threshold_w:
        return ModeDecision(mode="export_protect", reason="export_limit_exceeded")

    return ModeDecision(mode="business_normal", reason="normal_operation")
