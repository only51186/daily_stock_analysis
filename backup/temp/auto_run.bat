@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ====================================
echo A股自选股智能分析系统 - 自动运行脚本
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
echo 步骤 2: 运行选股策略
echo ====================================
echo.

python scripts\hs_mainboard_short_strategy.py

if !errorlevel! neq 0 (
    echo [错误] 选股策略运行失败
    echo [信息] 请查看日志文件: logs\strategy.log
    pause
    exit /b 1
)

echo.
echo [成功] 选股策略运行完成

echo.
echo ====================================
echo 步骤 3: 运行每日复盘
echo ====================================
echo.

python scripts\daily_review.py

if !errorlevel! neq 0 (
    echo [警告] 每日复盘运行失败
    echo [信息] 请查看日志文件: logs\strategy.log
) else (
    echo [成功] 每日复盘运行完成
)

echo.
echo ====================================
echo 所有任务完成！
echo ====================================
echo.
echo 日志文件位置:
echo   - 选股策略日志: logs\strategy.log
echo   - 回测日志: logs\backtest.log
echo.
echo 按任意键退出...
pause >nul
