from typing import Any, Dict

from ..control import arbitrate_mode, build_site_state, plan_export_protect
from ..device_semantics import snapshot_supports_write
from ..logger import get_logger
from .base import StrategyBase


MODE_LABELS = {
    "manual_override": "人工接管",
    "safe_hold": "保守运行",
    "export_protect": "反送保护",
    "business_normal": "正常运行",
}

MODE_DESCRIPTIONS = {
    "manual_override": "人工接管时暂停自动模式控制。",
    "safe_hold": "关键测量缺失或不可信时，系统只保留监控和保守动作。",
    "export_protect": "反送功率超限时，优先用储能、充电负荷和光伏限发消纳光伏。",
    "business_normal": "默认模式，系统保持监控和轻量运行。",
}


def _int_value(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


class ModeControllerStrategy(StrategyBase):
    """Single mode-based controller for the first export-protection iteration."""

    def __init__(self, config: Dict[str, Any], device_manager: Any, data_collector: Any):
        super().__init__(config, device_manager)
        self.data_collector = data_collector
        self.logger = get_logger("ModeControllerStrategy")
        self.state_config = dict(config.get("state", {}))
        self.mode_config = dict(config.get("mode", {}))
        self.use_simulated_devices = bool(config.get("use_simulated_devices", True))
        self.last_mode = "business_normal"
        self.last_reason = "not_started"
        self.last_actions: list[dict[str, Any]] = []

    def start(self) -> bool:
        self.enabled = True
        self.logger.info("启动模式控制器")
        return True

    def stop(self) -> bool:
        self.enabled = False
        self.logger.info("停止模式控制器")
        return True

    def execute(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled", "mode": self.last_mode, "actions": []}

        context = self._evaluate_runtime()
        decision = context["effective_decision"]
        plan = context["plan"]

        self.last_mode = decision["mode"]
        self.last_reason = decision["reason"]

        if decision["mode"] == "export_protect" and plan is not None:
            self._execute_plan(plan)
            self.last_actions = [action.__dict__.copy() for action in plan.actions]
            return {
                "status": "executed",
                "mode": decision["mode"],
                "reason": decision["reason"],
                "actions": self.last_actions,
                "remaining_gap_w": plan.remaining_gap_w,
            }

        self.last_actions = []
        return {
            "status": "executed",
            "mode": decision["mode"],
            "reason": decision["reason"],
            "actions": [],
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "mode": self.last_mode,
            "reason": self.last_reason,
            "actions": self.last_actions,
            "config": self.config,
        }

    def get_mode_summary(self) -> Dict[str, Any]:
        context = self._evaluate_runtime()
        state = context["site_state"]
        effective = context["effective_decision"]
        blockers = list(context["blockers"])
        participating_devices = context["participating_devices"]
        active_devices = self.device_manager.get_devices()
        candidate_devices = (
            self.device_manager.get_device_candidates()
            if hasattr(self.device_manager, "get_device_candidates")
            else []
        )

        if not active_devices:
            blockers.append("no_active_devices")

        return {
            "current_mode": effective["mode"],
            "current_mode_label": MODE_LABELS.get(effective["mode"], effective["mode"]),
            "current_reason": effective["reason"],
            "control_state": context["control_state"],
            "supported_modes": context["supported_modes"],
            "key_measurements": {
                "timestamp": state.timestamp.isoformat(),
                "grid_power_w": state.grid_power_w,
                "pv_power_w": state.pv_power_w,
            },
            "trust": {
                "trusted": state.trusted,
                "issues": list(state.trust_issues),
            },
            "blockers": blockers,
            "counts": {
                "active_devices": len(active_devices),
                "online_devices": sum(
                    1 for device in active_devices
                    if str(device.get("status", "online")).lower() == "online"
                ),
                "participating_devices": len(participating_devices),
                "candidate_devices": len(candidate_devices),
            },
            "participating_devices": participating_devices,
            "recent_actions": list(self.last_actions),
            "use_simulated_devices": self.use_simulated_devices,
        }

    def get_mode_config(self) -> Dict[str, Any]:
        return {
            "use_simulated_devices": self.use_simulated_devices,
            "state": {
                "max_data_age_seconds": int(self.state_config.get("max_data_age_seconds", 30)),
                "manual_override": bool(self.state_config.get("manual_override", False)),
            },
            "modes": {
                "manual_override": self._build_mode_config_entry(
                    "manual_override",
                    enabled=True,
                    configurable=True,
                    toggleable=False,
                    settings={
                        "active": bool(self.state_config.get("manual_override", False)),
                    },
                    fields=[
                        self._build_field(
                            "active",
                            "手动接管激活",
                            "boolean",
                            description="开启后系统强制进入人工接管模式。",
                        )
                    ],
                ),
                "safe_hold": self._build_mode_config_entry(
                    "safe_hold",
                    enabled=True,
                    configurable=True,
                    toggleable=False,
                    settings={
                        "max_data_age_seconds": int(self.state_config.get("max_data_age_seconds", 30)),
                    },
                    fields=[
                        self._build_field(
                            "max_data_age_seconds",
                            "最大数据时效（秒）",
                            "number",
                            min_value=1,
                            step=1,
                            description="超过该时效的关键测量会触发保守运行。",
                        )
                    ],
                ),
                "business_normal": self._build_mode_config_entry(
                    "business_normal",
                    enabled=True,
                    configurable=False,
                    toggleable=False,
                ),
                "export_protect": self._build_mode_config_entry(
                    "export_protect",
                    enabled=bool(self.mode_config.get("export_protect_enabled", True)),
                    configurable=True,
                    toggleable=True,
                    settings={
                        "export_limit_w": int(self.mode_config.get("export_limit_w", 5000)),
                        "export_enter_ratio": float(self.mode_config.get("export_enter_ratio", 1.0)),
                        "storage_soc_soft_limit": float(self.mode_config.get("storage_soc_soft_limit", 95)),
                    },
                    fields=[
                        self._build_field(
                            "export_limit_w",
                            "反送上限（W）",
                            "number",
                            min_value=0,
                            step=100,
                        ),
                        self._build_field(
                            "export_enter_ratio",
                            "进入比例",
                            "number",
                            min_value=0,
                            step=0.05,
                        ),
                        self._build_field(
                            "storage_soc_soft_limit",
                            "储能 SOC 软上限",
                            "number",
                            min_value=0,
                            max_value=100,
                            step=1,
                        ),
                    ],
                ),
            },
        }

    def update_mode_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        if "use_simulated_devices" in updates:
            self.use_simulated_devices = bool(updates["use_simulated_devices"])
            self.config["use_simulated_devices"] = self.use_simulated_devices

        state_updates = updates.get("state", {})
        if "max_data_age_seconds" in state_updates:
            self.state_config["max_data_age_seconds"] = int(state_updates["max_data_age_seconds"])
        if "manual_override" in state_updates:
            self.state_config["manual_override"] = bool(state_updates["manual_override"])

        manual_override_updates = updates.get("modes", {}).get("manual_override", {})
        manual_override_settings = manual_override_updates.get("settings", {})
        if "active" in manual_override_settings:
            self.state_config["manual_override"] = bool(manual_override_settings["active"])

        safe_hold_updates = updates.get("modes", {}).get("safe_hold", {})
        safe_hold_settings = safe_hold_updates.get("settings", {})
        if "max_data_age_seconds" in safe_hold_settings:
            self.state_config["max_data_age_seconds"] = int(safe_hold_settings["max_data_age_seconds"])

        mode_updates = updates.get("modes", {}).get("export_protect", {})
        if "enabled" in mode_updates:
            self.mode_config["export_protect_enabled"] = bool(mode_updates["enabled"])

        settings_updates = mode_updates.get("settings", {})
        for key in ("export_limit_w", "export_enter_ratio", "storage_soc_soft_limit"):
            if key in settings_updates:
                self.mode_config[key] = settings_updates[key]

        self.config["state"] = dict(self.state_config)
        self.config["mode"] = dict(self.mode_config)
        return self.get_mode_config()

    def _build_mode_config_entry(
        self,
        mode_name: str,
        enabled: bool,
        configurable: bool,
        toggleable: bool,
        settings: Dict[str, Any] | None = None,
        fields: list[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        return {
            "name": mode_name,
            "label": MODE_LABELS.get(mode_name, mode_name),
            "description": MODE_DESCRIPTIONS.get(mode_name, ""),
            "enabled": enabled,
            "configurable": configurable,
            "toggleable": toggleable,
            "settings": settings or {},
            "fields": fields or [],
        }

    def _build_field(
        self,
        key: str,
        label: str,
        field_type: str,
        description: str | None = None,
        min_value: float | int | None = None,
        max_value: float | int | None = None,
        step: float | int | None = None,
    ) -> Dict[str, Any]:
        field: Dict[str, Any] = {
            "key": key,
            "label": label,
            "type": field_type,
        }
        if description:
            field["description"] = description
        if min_value is not None:
            field["min"] = min_value
        if max_value is not None:
            field["max"] = max_value
        if step is not None:
            field["step"] = step
        return field

    def _evaluate_runtime(self) -> Dict[str, Any]:
        filtered_snapshots = self._filter_snapshots(self.data_collector.get_latest_data())
        site_state = build_site_state(filtered_snapshots, self.state_config)
        raw_decision = arbitrate_mode(site_state, self.mode_config)
        effective_decision = {"mode": raw_decision.mode, "reason": raw_decision.reason}
        plan = None
        blockers: list[str] = []

        if raw_decision.mode == "export_protect":
            plan = plan_export_protect(site_state, self.mode_config)
            if not plan.actions:
                effective_decision = {
                    "mode": "business_normal",
                    "reason": "no_export_control_capability",
                }
                blockers.append("no_export_control_capability")
                plan = None

        if raw_decision.mode == "safe_hold":
            blockers.extend(site_state.trust_issues)

        participating_devices = self._get_participating_devices(filtered_snapshots)
        control_state = "closed_loop" if self._has_closed_loop_capability(site_state, plan) else "monitor_only"
        supported_modes = self._build_supported_modes(site_state, raw_decision, effective_decision, plan)

        return {
            "filtered_snapshots": filtered_snapshots,
            "site_state": site_state,
            "raw_decision": {"mode": raw_decision.mode, "reason": raw_decision.reason},
            "effective_decision": effective_decision,
            "plan": plan,
            "blockers": blockers,
            "control_state": control_state,
            "participating_devices": participating_devices,
            "supported_modes": supported_modes,
        }

    def _has_closed_loop_capability(self, state: Any, plan: Any) -> bool:
        if not state.trusted:
            return False
        if plan is not None and plan.actions:
            return True

        for snapshot in state.snapshots.values():
            device_type = snapshot.get("device_type")
            data = snapshot.get("data", {})
            status = str(data.get("status", "online")).lower()
            if status in {"offline", "fault", "error"}:
                continue

            if (
                device_type == "energy_storage"
                and snapshot_supports_write(snapshot, "mode", "charge_power")
                and _int_value(data.get("max_charge_power")) > 0
            ):
                return True
            if device_type in {"charging_station", "charging_connector"}:
                current_power = _int_value(data.get("power"))
                max_power = _int_value(data.get("max_power"), current_power)
                if snapshot_supports_write(snapshot, "power_limit") and current_power > 0 and max_power > current_power:
                    return True
            if device_type == "pv":
                current_limit = _int_value(data.get("power_limit"), _int_value(data.get("power")))
                min_limit = _int_value(data.get("min_power_limit"))
                if snapshot_supports_write(snapshot, "power_limit") and current_limit > min_limit:
                    return True

        return False

    def _build_supported_modes(
        self,
        state: Any,
        raw_decision: Dict[str, Any] | Any,
        effective_decision: Dict[str, Any],
        plan: Any,
    ) -> list[Dict[str, Any]]:
        export_enabled = bool(self.mode_config.get("export_protect_enabled", True))
        export_threshold_w = -float(self.mode_config.get("export_limit_w", 0)) * float(
            self.mode_config.get("export_enter_ratio", 1.0)
        )
        export_requested = state.grid_power_w is not None and state.grid_power_w <= export_threshold_w
        export_available = False
        export_reason = "export_within_limit"

        if not export_enabled:
            export_reason = "mode_disabled"
        elif not state.trusted:
            export_reason = "site_state_untrusted"
        elif state.grid_power_w is None:
            export_reason = "missing_grid_power"
        elif not export_requested:
            export_reason = "export_within_limit"
        elif plan is None:
            export_reason = "no_export_control_capability"
        else:
            export_available = True
            export_reason = "export_limit_exceeded"

        modes = [
            {
                "name": "manual_override",
                "label": MODE_LABELS["manual_override"],
                "description": MODE_DESCRIPTIONS["manual_override"],
                "enabled": True,
                "available": bool(state.manual_override),
                "active": effective_decision["mode"] == "manual_override",
                "reason": "manual_override_enabled" if state.manual_override else "manual_override_inactive",
            },
            {
                "name": "safe_hold",
                "label": MODE_LABELS["safe_hold"],
                "description": MODE_DESCRIPTIONS["safe_hold"],
                "enabled": True,
                "available": not state.trusted,
                "active": effective_decision["mode"] == "safe_hold",
                "reason": "untrusted_site_state" if not state.trusted else "site_state_trusted",
            },
            {
                "name": "export_protect",
                "label": MODE_LABELS["export_protect"],
                "description": MODE_DESCRIPTIONS["export_protect"],
                "enabled": export_enabled,
                "available": export_available,
                "active": effective_decision["mode"] == "export_protect",
                "reason": export_reason,
            },
            {
                "name": "business_normal",
                "label": MODE_LABELS["business_normal"],
                "description": MODE_DESCRIPTIONS["business_normal"],
                "enabled": True,
                "available": state.trusted,
                "active": effective_decision["mode"] == "business_normal",
                "reason": effective_decision["reason"] if effective_decision["mode"] == "business_normal" else "inactive",
            },
        ]
        return modes

    def _get_participating_devices(self, snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
        devices: list[dict[str, Any]] = []
        for snapshot in snapshots:
            device_id = snapshot.get("device_id")
            if not device_id:
                continue

            device_info = self.device_manager.get_device(device_id) if hasattr(self.device_manager, "get_device") else None
            base_info = {
                "device_id": device_id,
                "device_type": snapshot.get("device_type"),
            }
            if device_info:
                base_info.update(
                    {
                        "source": device_info.get("source", "real"),
                        "protocol": device_info.get("protocol"),
                        "status": device_info.get("status", "online"),
                    }
                )
                if "capabilities" in device_info:
                    base_info["capabilities"] = device_info.get("capabilities")
                if "pile_id" in device_info:
                    base_info["pile_id"] = device_info.get("pile_id")
                if "connector_id" in device_info:
                    base_info["connector_id"] = device_info.get("connector_id")
            devices.append(base_info)
        return devices

    def _execute_plan(self, plan: Any):
        for action in plan.actions:
            if action.action == "set_charge_power":
                self.device_manager.write_device_data(action.device_id, "mode", "charge")
                self.device_manager.write_device_data(action.device_id, "charge_power", action.value_w)
            elif action.action == "set_power_limit":
                self.device_manager.write_device_data(action.device_id, "power_limit", action.value_w)

    def _filter_snapshots(self, snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
        filtered_snapshots: list[dict[str, Any]] = []

        for snapshot in snapshots:
            device_id = snapshot.get("device_id")
            device_info = self.device_manager.get_device(device_id) if hasattr(self.device_manager, "get_device") else None

            if device_info:
                if str(device_info.get("status", "online")).lower() == "offline":
                    continue
                if not self.use_simulated_devices and device_info.get("source") == "simulated":
                    continue

            filtered_snapshots.append(snapshot)

        return filtered_snapshots
