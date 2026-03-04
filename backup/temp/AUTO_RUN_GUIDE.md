# 自动运行脚本使用指南

## 概述

本目录包含两个批处理脚本，用于自动化运行股票分析系统：

1. **auto_run.bat** - 自动运行选股策略和每日复盘
2. **run_backtest.bat** - 运行策略回测

## 功能特性

### auto_run.bat

- ✅ 自动激活虚拟环境
- ✅ 自动拉取 Git 仓库最新代码
- ✅ 运行选股策略（hs_mainboard_short_strategy.py）
- ✅ 运行每日复盘（daily_review.py）
- ✅ 自动推送结果到豆包

### run_backtest.bat

- ✅ 自动激活虚拟环境
- ✅ 自动拉取 Git 仓库最新代码
- ✅ 运行策略回测（strategy_backtest.py）
- ✅ 自动打开回测结果图表

## 使用方法

### 首次使用（创建虚拟环境）

1. 打开命令提示符（CMD）或 PowerShell

2. 进入项目目录：
```bash
cd g:\豆包ide\daily_stock_analysis\daily_stock_analysis
```

3. 创建虚拟环境：
```bash
python -m venv venv
```

4. 激活虚拟环境：
```bash
venv\Scripts\activate
```

5. 安装依赖：
```bash
pip install -r requirements.txt
```

### 日常使用

#### 运行选股策略和每日复盘

双击 `auto_run.bat` 文件，或在命令行中运行：
```bash
auto_run.bat
```

#### 运行策略回测

双击 `run_backtest.bat` 文件，或在命令行中运行：
```bash
run_backtest.bat
```

## 日志文件

所有日志文件保存在 `logs/` 目录下：

- `strategy.log` - 选股策略日志
- `backtest.log` - 回测日志

## 注意事项

1. **Git 仓库**：脚本会自动检测是否在 Git 仓库中，如果是，会自动拉取最新代码
2. **虚拟环境**：脚本会自动检测并激活虚拟环境
3. **错误处理**：如果某个步骤失败，脚本会显示错误信息并退出
4. **日志查看**：如果运行失败，请查看相应的日志文件

## 定时任务设置

### Windows 任务计划程序

1. 打开"任务计划程序"（taskschd.msc）
2. 创建基本任务
3. 设置触发器（例如：每个工作日的 15:00）
4. 设置操作为"启动程序"
5. 浏览并选择 `auto_run.bat` 文件
6. 完成设置

### 推荐的定时任务

- **选股策略**：每个工作日的 15:00（收盘后）
- **每日复盘**：每个工作日的 09:00（开盘前）
- **策略回测**：每周日的 20:00

## 故障排除

### 虚拟环境激活失败

如果提示虚拟环境不存在，请先创建虚拟环境：
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Git 拉取失败

如果提示 Git 拉取失败，可能是以下原因：
- 网络连接问题
- 有未提交的本地更改
- 分支名称不正确

解决方法：
```bash
git status
git stash
git pull origin main
```

### 脚本运行失败

如果脚本运行失败，请查看日志文件：
- 选股策略：`logs/strategy.log`
- 回测：`logs/backtest.log`

## 高级配置

### 修改 Git 分支

如果需要从其他分支拉取代码，编辑批处理文件，将：
```batch
git pull origin main
```
改为：
```batch
git pull origin your-branch-name
```

### 禁用自动更新

如果不需要自动更新代码，注释掉 Git 相关的代码块。

### 添加更多任务

在批处理文件中添加更多的 Python 脚本调用：
```batch
echo [信息] 运行自定义脚本...
python scripts\your_script.py
```

## 快捷键配置（Trae IDE）

在 Trae IDE 中设置快捷键：

1. 打开 Trae 设置 → 键盘快捷键
2. 添加自定义快捷键：
   - `Ctrl+R` → 运行 `auto_run.bat`
   - `Ctrl+B` → 运行 `run_backtest.bat`

## 联系支持

如果遇到问题，请查看日志文件或联系技术支持。
