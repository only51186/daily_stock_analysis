# GitHub 部署指南

## 概述

本文档说明如何将 daily_stock_analysis 项目部署到 GitHub，确保在 GitHub Codespaces/Action 中正常运行。

## 前置要求

- GitHub 账户
- 豆包 API 密钥（从 https://console.volcengine.com/ark 获取）
- Tushare Token（可选，从 https://tushare.pro/register 获取）

## 部署步骤

### 1. 配置环境变量

在 GitHub 仓库中配置 Secrets：

1. 进入仓库的 Settings → Secrets and variables → Actions
2. 添加以下 Secrets：

| Secret 名称 | 说明 | 获取地址 |
|-----------|------|---------|
| `DOUBAO_API_KEY` | 豆包 API 密钥 | https://console.volcengine.com/ark |
| `TUSHARE_TOKEN` | Tushare Token（可选） | https://tushare.pro/register |

### 2. 创建 .env 文件（本地开发）

复制 `.env.example` 为 `.env` 并填入真实配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API 密钥：

```env
DOUBAO_API_KEY=your_doubao_api_key_here
TUSHARE_TOKEN=your_tushare_token_here
```

### 3. 在 GitHub Codespaces 中运行

1. 在 GitHub 仓库页面点击 "Code" → "Codespaces" → "Create codespace on main"
2. 等待 Codespaces 启动
3. 在终端中运行：

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（在 Codespaces 中）
echo "DOUBAO_API_KEY=your_doubao_api_key_here" >> .env
echo "TUSHARE_TOKEN=your_tushare_token_here" >> .env

# 运行项目
python main.py
```

### 4. 使用 GitHub Actions 自动化

项目已配置 GitHub Actions 工作流，可以自动运行以下任务：

- **CI**: 代码质量检查
- **每日分析**: 每天自动运行选股和回测
- **自动修复**: 自动修复代码问题

工作流文件位于 `.github/workflows/` 目录。

## 配置说明

### 环境变量优先级

1. 环境变量（最高优先级）
2. 配置文件（.env）
3. 默认值（最低优先级）

### 主要配置项

#### 豆包 API 配置

```env
DOUBAO_API_KEY=your_doubao_api_key_here
DOUBAO_MODEL=Doubao-Seedream-5.0-lite
DOUBAO_MAX_TOKENS=1000
DOUBAO_TEMPERATURE=0.7
```

#### 策略配置

```env
STRATEGY_PRICE_MIN=5.0
STRATEGY_PRICE_MAX=35.0
STRATEGY_TURNOVER_RATE_MIN=3.0
STRATEGY_TURNOVER_RATE_MAX=10.0
STRATEGY_VOLUME_RATIO_THRESHOLD=1.5
STRATEGY_HOLD_DAYS=2
```

#### 定时任务配置

```env
SCHEDULE_ENABLED=true
SCHEDULE_DATA_DOWNLOAD_TIMES=09:30,14:00
SCHEDULE_SELECTION_TIME=14:30
SCHEDULE_BACKTEST_TIME=20:00
```

## 跨平台兼容性

项目已适配 Windows/Linux/MacOS：

- 使用 `pathlib.Path` 处理路径，避免硬编码绝对路径
- 使用 `os.pathsep` 处理路径分隔符
- 使用 `platform` 模块检测操作系统
- 所有配置通过环境变量管理

## 敏感信息保护

以下内容已被移除或保护：

1. **API 密钥**: 已从代码中移除，通过环境变量管理
2. **绝对路径**: 已替换为相对路径
3. **硬编码参数**: 已迁移到配置文件

### .gitignore 配置

以下文件/目录不会被提交到 GitHub：

- `.env` - 环境变量文件
- `data/` - 数据目录
- `logs/` - 日志目录
- `data_cache/` - 缓存目录
- `__pycache__/` - Python 缓存
- `*.pyc` - 编译文件
- `venv/` - 虚拟环境

## 常见问题

### 1. API 密钥错误

**问题**: 运行时提示 API 密钥错误

**解决**: 确保 `.env` 文件中配置了正确的 `DOUBAO_API_KEY`

### 2. 路径错误

**问题**: 提示找不到文件或目录

**解决**: 确保在项目根目录运行，使用相对路径

### 3. 依赖安装失败

**问题**: `pip install` 失败

**解决**: 使用虚拟环境，确保 Python 版本 >= 3.10

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 4. 数据获取失败

**问题**: 无法获取股票数据

**解决**: 检查网络连接，确保数据源可用

## 功能验证

运行以下命令验证功能：

```bash
# 测试配置
python -c "from config.settings import get_settings; print(get_settings().project_root)"

# 测试数据源
python -c "from data_provider.multi_data_source import MultiDataSource; ds = MultiDataSource(); print(ds.get_stock_info('600000'))"

# 测试选股
python scripts/end_of_day_selector.py

# 测试回测
python scripts/strategy_backtest.py

# 测试推送
python -c "from utils.notification_sender import get_notification_sender; sender = get_notification_sender(); sender.send_custom_message('测试', '这是一条测试消息')"
```

## 性能优化

### 缓存机制

项目使用多级缓存：

1. **内存缓存**: 临时数据缓存
2. **文件缓存**: 持久化数据缓存（有效期 1 小时）
3. **数据源缓存**: 避免重复请求

### Token 优化

- 单条分析回复 token 消耗 ≤ 800
- 批量分析 token 消耗 ≤ 2000
- 剩余 token < 10% 时自动切换轻量化推理

## 监控和日志

### 日志文件

- `logs/strategy.log` - 策略日志
- `logs/backtest.log` - 回测日志
- `logs/data.log` - 数据日志
- `logs/error.log` - 错误日志

### 日志级别

可通过环境变量配置：

```env
LOG_LEVEL=INFO  # DEBUG/INFO/WARNING/ERROR/CRITICAL
```

## 更新和维护

### 更新代码

```bash
git pull origin main
```

### 更新依赖

```bash
pip install --upgrade -r requirements.txt
```

### 清理缓存

```bash
# 清理数据缓存
rm -rf data_cache/

# 清理日志
rm -rf logs/

# 清理 Python 缓存
find . -type d -name __pycache__ -exec rm -rf {} +
```

## 支持和反馈

如有问题，请：

1. 查看 [FAQ.md](docs/FAQ.md)
2. 提交 [Issue](https://github.com/your-repo/issues)
3. 查看 [完整指南](docs/full-guide.md)

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。
