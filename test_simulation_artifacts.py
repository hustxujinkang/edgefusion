from pathlib import Path


ROOT = Path(__file__).resolve().parent


def test_dashboard_template_exposes_simulation_scenario_controls():
    template = ROOT / "edgefusion" / "templates" / "index.html"
    content = template.read_text(encoding="utf-8")

    assert "simulationScenarioCard" in content
    assert "simulationScenarioSelect" in content
    assert "liveSnapshotList" in content
    assert "systemStatusBadge" in content
    assert "/api/simulation/scenarios" in content
    assert "/api/simulation/scenario" in content
    assert "/api/collector/latest" in content


def test_simulation_scenario_example_yaml_exists():
    example = ROOT / "docs" / "examples" / "simulation-scenarios.yaml"

    assert example.exists()

    content = example.read_text(encoding="utf-8")

    assert "sunny_midday" in content
    assert "cloud_pass" in content
    assert "low_soc" in content
    assert "charger_rush" in content
