@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ====================================
echo A股自选股智能分析系统 - 快速启动
echo ====================================
echo.

REM 检查虚拟环境
if not defined VIRTUAL_ENV (
    echo [信息] 正在激活虚拟环境...
    if exist "venv\Scripts\activate.bat" (
        call venv\Scripts\activate.bat
        echo [成功] 虚拟环境已激活
    ) else (
        echo [错误] 虚拟环境不存在，请先创建虚拟环境：
        echo.
        echo   python -m venv venv
        echo   venv\Scripts\activate
        echo   pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
)

:menu
echo.
echo ====================================
echo 请选择要执行的操作：
echo ====================================
echo.
echo  [1] 启动股票走势预测界面
echo  [2] 立即运行选股策略
echo  [3] 立即运行策略回测
echo  [4] 立即运行每日复盘
echo  [5] 运行所有任务（选股+复盘+回测）
echo  [6] 启动定时调度器（后台运行）
echo  [7] 查看日志文件
echo  [8] 退出
echo.
echo ====================================
set /p choice="请输入选项 [1-8]: "

if "%choice%"=="1" goto ui
if "%choice%"=="2" goto selection
if "%choice%"=="3" goto backtest
if "%choice%"=="4" goto review
if "%choice%"=="5" goto all
if "%choice%"=="6" goto scheduler
if "%choice%"=="7" goto logs
if "%choice%"=="8" goto exit
goto menu

:ui
echo.
echo [信息] 正在启动股票走势预测界面...
python scripts\stock_prediction_ui.py
goto menu

:selection
echo.
echo [信息] 正在运行选股策略...
python scripts\unified_scheduler.py --selection
echo.
echo [信息] 选股策略运行完成
echo.
pause
goto menu

:backtest
echo.
echo [信息] 正在运行策略回测...
python scripts\unified_scheduler.py --backtest
echo.
echo [信息] 策略回测运行完成
echo.
pause
goto menu

:review
echo.
echo [信息] 正在运行每日复盘...
python scripts\unified_scheduler.py --review
echo.
echo [信息] 每日复盘运行完成
echo.
pause
goto menu

:all
echo.
echo [信息] 正在运行所有任务...
python scripts\unified_scheduler.py --run-all
echo.
echo [信息] 所有任务运行完成
echo.
pause
goto menu

:scheduler
echo.
echo [信息] 正在启动定时调度器...
echo [信息] 调度器将在后台运行，按 Ctrl+C 停止
echo.
python scripts\unified_scheduler.py --scheduler
goto menu

:logs
echo.
echo ====================================
echo 日志文件列表
echo ====================================
echo.
if exist "logs" (
    dir /b logs\*.log 2>nul
    if errorlevel 1 (
        echo [信息] 暂无日志文件
    )
) else (
    echo [信息] 日志目录不存在
)
echo.
echo [信息] 日志文件位置: logs\
echo.
pause
goto menu

:exit
echo.
echo [信息] 感谢使用，再见！
echo.
timeout /t 2 >nul
exit /b 0
