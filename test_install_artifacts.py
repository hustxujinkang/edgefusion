from pathlib import Path


ROOT = Path(__file__).resolve().parent


def test_service_template_is_named_as_template():
    assert (ROOT / "edgefusion.service.template").exists()
    assert not (ROOT / "edgefusion.service").exists()


def test_install_and_run_scripts_are_removed():
    assert not (ROOT / "install.sh").exists()
    assert not (ROOT / "run.sh").exists()


def test_run_local_script_bootstraps_local_environment_and_uses_project_local_paths():
    run_local = ROOT / "run_local.sh"

    assert run_local.exists()

    content = run_local.read_text(encoding="utf-8")

    assert "python3.10 python3.11 python3.12 python3" in content
    assert '"$PYTHON_BIN" -m venv .venv' in content
    assert '.venv/bin/python -m pip install -r "$REQ_FILE"' in content
    assert 'REQ_FILE="${EDGEFUSION_REQUIREMENTS_FILE:-requirements.txt}"' in content
    assert "EDGEFUSION_CONFIG_FILE" in content
    assert "EDGEFUSION_LOG_DIR" in content
    assert "EDGEFUSION_DB_PATH" in content
    assert "exec .venv/bin/python -m edgefusion.main" in content


def test_deploy_script_handles_production_installation_without_install_or_run_scripts():
    deploy_script = ROOT / "deploy.sh"
    content = deploy_script.read_text(encoding="utf-8")

    assert '"$PYTHON_BIN" -m venv .venv' in content
    assert '.venv/bin/python -m pip install -r "$REQ_FILE"' in content
    assert 'REQ_FILE="${EDGEFUSION_REQUIREMENTS_FILE:-requirements-prod.txt}"' in content
    assert "install.sh" not in content
    assert "run.sh" not in content
    assert "edgefusion.service.template" in content


def test_service_template_starts_python_directly():
    template = ROOT / "edgefusion.service.template"
    content = template.read_text(encoding="utf-8")

    assert "ExecStart=__EDGEFUSION_PROJECT_DIR__/.venv/bin/python -m edgefusion.main" in content
    assert "run.sh" not in content
