@echo off
setlocal

cd /d "%~dp0"

set "VENV_DIR=.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "REINSTALL=0"
set "BOOTSTRAP_PY="

if /I "%~1"=="--reinstall" set "REINSTALL=1"

echo EdgeFusion backend launcher
echo ==========================

if exist "%VENV_PY%" (
    call :venv_supported
    if errorlevel 1 (
        echo [ERROR] Existing .venv uses an unsupported Python version.
        echo [ERROR] Remove .venv and install Python 3.10, 3.11, or 3.12.
        pause
        exit /b 1
    )
    goto install_if_needed
)

call :find_bootstrap_python

if not defined BOOTSTRAP_PY (
    echo [ERROR] Python 3.10, 3.11, or 3.12 was not found in PATH.
    echo [ERROR] Install a supported Python, or add python.exe/py.exe to PATH, then retry.
    pause
    exit /b 1
)

echo [INIT] Creating virtual environment...
%BOOTSTRAP_PY% -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)
set "REINSTALL=1"

:install_if_needed
if "%REINSTALL%"=="0" (
    "%VENV_PY%" -c "import yaml, flask, sqlalchemy" >nul 2>nul
    if errorlevel 1 set "REINSTALL=1"
)

if "%REINSTALL%"=="1" (
    echo [INIT] Installing dependencies...
    "%VENV_PY%" -m pip install --upgrade pip
    if errorlevel 1 (
        echo [ERROR] Failed to upgrade pip.
        pause
        exit /b 1
    )

    "%VENV_PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed.
        pause
        exit /b 1
    )
)

echo [RUN] Starting EdgeFusion...
"%VENV_PY%" -m edgefusion.main
if errorlevel 1 (
    echo [ERROR] EdgeFusion exited with error.
    pause
    exit /b 1
)

endlocal
goto :eof

:find_bootstrap_python
call :try_python py -3.10
call :try_python py -3.11
call :try_python py -3.12
call :try_python python
exit /b 0

:try_python
if defined BOOTSTRAP_PY exit /b 0
if "%~1"=="" exit /b 0

set "_PY_CMD=%~1"
if not "%~2"=="" set "_PY_CMD=%_PY_CMD% %~2"

%_PY_CMD% -c "import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] < (3, 13) else 1)" >nul 2>nul
if not errorlevel 1 set "BOOTSTRAP_PY=%_PY_CMD%"

set "_PY_CMD="
exit /b 0

:venv_supported
"%VENV_PY%" -c "import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] < (3, 13) else 1)" >nul 2>nul
exit /b %errorlevel%
