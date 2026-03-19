from pathlib import Path


ROOT = Path(__file__).resolve().parent


def assert_contains_any(content: str, *patterns: str):
    assert any(pattern in content for pattern in patterns), patterns


def test_service_template_is_named_as_template():
    assert (ROOT / "edgefusion.service.template").exists()
    assert not (ROOT / "edgefusion.service").exists()


def test_install_and_run_scripts_are_removed():
    assert not (ROOT / "install.sh").exists()
    assert not (ROOT / "run.sh").exists()


def test_uninstall_script_exists_and_defaults_to_keep_data():
    uninstall_script = ROOT / "uninstall.sh"

    assert uninstall_script.exists()

    content = uninstall_script.read_text(encoding="utf-8")

    assert '. "$PROJECT_DIR/runtime-env.sh"' in content
    assert 'PURGE=0' in content
    assert '[ "${1:-}" = "--purge" ]' in content
    assert 'systemctl stop "$EDGEFUSION_SERVICE_NAME"' in content
    assert 'systemctl disable "$EDGEFUSION_SERVICE_NAME"' in content
    assert 'rm -f "$SERVICE_FILE"' in content
    assert 'rm -rf "$EDGEFUSION_APP_DIR"' in content
    assert 'if [ "$PURGE" -eq 1 ]; then' in content
    assert 'rm -rf "$EDGEFUSION_CONFIG_DIR"' in content
    assert 'rm -rf "$EDGEFUSION_DATA_DIR"' in content
    assert 'rm -rf "$EDGEFUSION_LOG_DIR"' in content


def test_run_local_script_bootstraps_local_environment_and_uses_project_local_paths():
    run_local = ROOT / "run_local.sh"

    assert run_local.exists()

    content = run_local.read_text(encoding="utf-8")

    assert "python3.10 python3.11 python3.12 python3" in content
    assert 'readonly VENV_DIR="$PROJECT_DIR/.venv"' in content
    assert 'readonly VENV_PYTHON="$VENV_DIR/bin/python"' in content
    assert_contains_any(content, '"$PYTHON_BIN" -m venv .venv', '"$PYTHON_BIN" -m venv "$VENV_DIR"')
    assert_contains_any(content, '.venv/bin/python -m pip install -r "$REQ_FILE"', '"$VENV_PYTHON" -m pip install -r "$REQ_FILE"')
    assert 'REQ_FILE="${EDGEFUSION_REQUIREMENTS_FILE:-requirements.txt}"' in content
    assert "EDGEFUSION_CONFIG_FILE" in content
    assert "EDGEFUSION_LOG_DIR" in content
    assert "EDGEFUSION_DB_PATH" in content
    assert_contains_any(content, 'exec .venv/bin/python -m edgefusion.main', 'exec "$VENV_PYTHON" -m edgefusion.main')


def test_deploy_script_handles_production_installation_without_install_or_run_scripts():
    deploy_script = ROOT / "deploy.sh"
    content = deploy_script.read_text(encoding="utf-8")

    assert '"$PYTHON_BIN" -m venv .venv' in content
    assert 'local venv_python="$EDGEFUSION_APP_DIR/.venv/bin/python"' in content
    assert_contains_any(content, '.venv/bin/python -m pip install -r "$REQ_FILE"', '"$venv_python" -m pip install -r "$req_file"')
    assert_contains_any(content, 'REQ_FILE="${EDGEFUSION_REQUIREMENTS_FILE:-requirements-prod.txt}"', 'local req_file="${EDGEFUSION_REQUIREMENTS_FILE:-requirements-prod.txt}"')
    assert "./install.sh" not in content
    assert "$EDGEFUSION_APP_DIR/install.sh" not in content
    assert "./run.sh" not in content
    assert "$EDGEFUSION_APP_DIR/run.sh" not in content
    assert "edgefusion.service.template" in content


def test_service_template_starts_python_directly():
    template = ROOT / "edgefusion.service.template"
    content = template.read_text(encoding="utf-8")

    assert "Environment=PYTHONIOENCODING" not in content
    assert "Environment=PYTHONUTF8" not in content
    assert "ExecStart=__EDGEFUSION_PROJECT_DIR__/.venv/bin/python -m edgefusion.main" in content
    assert "run.sh" not in content


def test_runtime_package_uses_logger_instead_of_print_statements():
    package_files = list((ROOT / "edgefusion").rglob("*.py"))
    offenders = []

    for file_path in package_files:
        if "__pycache__" in file_path.parts:
            continue

        content = file_path.read_text(encoding="utf-8")
        if "print(" in content:
            offenders.append(file_path.relative_to(ROOT).as_posix())

    assert offenders == []
