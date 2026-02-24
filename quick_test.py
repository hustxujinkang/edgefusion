#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速测试脚本 - 一键验证EdgeFusion系统功能
"""

import subprocess
import time
import sys
import os
import threading

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_step(step, text):
    print(f"\n[{step}] {text}")

def check_dependencies():
    print_header("检查依赖")
    try:
        import flask
        print_step("✓", "Flask 已安装")
    except ImportError:
        print_step("✗", "Flask 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "flask"], check=True)
    
    try:
        import pymodbus
        print_step("✓", "pymodbus 已安装")
    except ImportError:
        print_step("✗", "pymodbus 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pymodbus"], check=True)
    
    try:
        import sqlalchemy
        print_step("✓", "SQLAlchemy 已安装")
    except ImportError:
        print_step("✗", "SQLAlchemy 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "sqlalchemy"], check=True)

def main():
    print_header("EdgeFusion 快速测试向导")
    print("\n这个脚本将引导你完成系统的快速测试。")
    print("请按照以下步骤操作：\n")
    
    steps = [
        "步骤 1: 检查依赖项",
        "步骤 2: 启动 Modbus 充电桩模拟器（需要在新终端运行）",
        "步骤 3: 启动 EdgeFusion 主程序（需要在新终端运行）",
        "步骤 4: 打开浏览器访问监控界面",
        "步骤 5: 在Web界面中添加设备并测试功能"
    ]
    
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")
    
    print("\n让我们开始吧！\n")
    
    # 检查依赖
    check_dependencies()
    
    print_header("下一步操作")
    print("\n依赖检查完成！现在请按照以下步骤操作：\n")
    
    print("📋 操作指南：")
    print("-" * 60)
    print("\n1️⃣  打开一个新的终端窗口，运行模拟器：")
    print("    conda activate edgefusion-env")
    print("    python modbus_charger_simulator.py")
    print("\n2️⃣  打开另一个新的终端窗口，运行主程序：")
    print("    conda activate edgefusion-env")
    print("    python test_edgefusion.py")
    print("\n3️⃣  等待两个程序都启动后，打开浏览器访问：")
    print("    http://localhost:5000")
    print("\n4️⃣  在Web界面中：")
    print("    - 点击 '添加设备' 标签页")
    print("    - 填写配置（默认值即可）")
    print("    - 测试连接并添加设备")
    print("    - 转到 '设备管理' 页面操作设备")
    print("\n" + "="*60)
    print("📖 详细说明请查看: QUICK_START_GUIDE.md")
    print("="*60 + "\n")
    
    print("💡 提示：按 Ctrl+C 可以停止正在运行的程序")

if __name__ == "__main__":
    main()
