from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable


GRID_DEVICE_TYPES = {"grid", "grid_meter"}


@dataclass
class SiteState:
    timestamp: datetime
    grid_power_w: float | None
    pv_power_w: float
    trusted: bool
    trust_issues: list[str] = field(default_factory=list)
    manual_override: bool = False
    critical_fault: bool = False
    dispatch_event_active: bool = False
    snapshots: dict[str, dict[str, Any]] = field(default_factory=dict)


def _parse_timestamp(raw_timestamp: str | None) -> datetime:
    if raw_timestamp:
        return datetime.fromisoformat(raw_timestamp)
    return datetime.now()


def build_site_state(
    snapshots: Iterable[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> SiteState:
    config = config or {}
    max_data_age_seconds = config.get("max_data_age_seconds", 30)

    latest_by_device: dict[str, dict[str, Any]] = {}
    latest_timestamp = datetime.min
    grid_power_w: float | None = None
    pv_power_w = 0.0
    trust_issues: list[str] = []

    for snapshot in snapshots:
        device_id = snapshot.get("device_id")
        if not device_id:
            continue

        snapshot_timestamp = _parse_timestamp(snapshot.get("timestamp"))
        existing = latest_by_device.get(device_id)
        if existing is None or _parse_timestamp(existing.get("timestamp")) <= snapshot_timestamp:
            latest_by_device[device_id] = snapshot

        if snapshot_timestamp > latest_timestamp:
            latest_timestamp = snapshot_timestamp

    if latest_timestamp == datetime.min:
        latest_timestamp = datetime.now()

    for snapshot in latest_by_device.values():
        device_type = snapshot.get("device_type")
        data = snapshot.get("data", {})
        snapshot_timestamp = _parse_timestamp(snapshot.get("timestamp"))

        if (latest_timestamp - snapshot_timestamp).total_seconds() > max_data_age_seconds:
            trust_issues.append(f"stale:{snapshot.get('device_id')}")

        if device_type in GRID_DEVICE_TYPES and data.get("power") is not None:
            grid_power_w = float(data["power"])

        if device_type == "pv" and data.get("power") is not None:
            pv_power_w += float(data["power"])

    if grid_power_w is None:
        trust_issues.append("missing_grid_power")

    return SiteState(
        timestamp=latest_timestamp,
        grid_power_w=grid_power_w,
        pv_power_w=pv_power_w,
        trusted=not trust_issues,
        trust_issues=trust_issues,
        manual_override=bool(config.get("manual_override", False)),
        critical_fault=bool(config.get("critical_fault", False)),
        dispatch_event_active=bool(config.get("dispatch_event_active", False)),
        snapshots=latest_by_device,
    )
