@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ====================================
echo A股自选股智能分析系统 - 回测脚本
echo ====================================
echo.

REM 检查是否在虚拟环境中
if not defined VIRTUAL_ENV (
    echo [信息] 未检测到虚拟环境，正在激活...
    if exist "venv\Scripts\activate.bat" (
        call venv\Scripts\activate.bat
        echo [成功] 虚拟环境已激活
    ) else (
        echo [警告] 虚拟环境不存在，请先运行以下命令创建虚拟环境：
        echo         python -m venv venv
        echo         venv\Scripts\activate
        echo         pip install -r requirements.txt
        pause
        exit /b 1
    )
) else (
    echo [信息] 虚拟环境已激活: %VIRTUAL_ENV%
)

echo.
echo ====================================
echo 步骤 1: 更新代码
echo ====================================
echo.

REM 检查是否在 Git 仓库中
if exist ".git" (
    echo [信息] 检测到 Git 仓库，正在拉取最新代码...
    git pull origin main
    if !errorlevel! equ 0 (
        echo [成功] 代码更新成功
    ) else (
        echo [警告] 代码更新失败，继续使用当前代码运行
    )
) else (
    echo [信息] 未检测到 Git 仓库，跳过代码更新
)

echo.
echo ====================================
echo 步骤 2: 运行策略回测
echo ====================================
echo.

python scripts\strategy_backtest.py

if !errorlevel! neq 0 (
    echo [错误] 策略回测运行失败
    echo [信息] 请查看日志文件: logs\backtest.log
    pause
    exit /b 1
)

echo.
echo [成功] 策略回测运行完成

echo.
echo ====================================
echo 步骤 3: 打开回测报告
echo ====================================
echo.

if exist "backtest_result.png" (
    echo [信息] 正在打开回测结果图表...
    start backtest_result.png
) else (
    echo [警告] 未找到回测结果图表: backtest_result.png
)

if exist "backtest_report.csv" (
    echo [信息] 回测报告已保存: backtest_report.csv
)

echo.
echo ====================================
echo 回测完成！
echo ====================================
echo.
echo 日志文件位置:
echo   - 回测日志: logs\backtest.log
echo   - 回测结果图表: backtest_result.png
echo   - 回测报告: backtest_report.csv
echo.
echo 按任意键退出...
pause >nul
