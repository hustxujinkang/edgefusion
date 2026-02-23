@echo off

REM EdgeFusion启动脚本

cd /d %~dp0

echo EdgeFusion 台区智能融合终端后台程序
 echo ================================

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Python未安装或未添加到环境变量
    pause
    exit /b 1
)

REM 检查并安装依赖
echo 检查依赖...
if exist requirements.txt (
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo 错误: 安装依赖失败
        pause
        exit /b 1
    )
)

echo 启动EdgeFusion应用...
python -m edgefusion.main

pause
