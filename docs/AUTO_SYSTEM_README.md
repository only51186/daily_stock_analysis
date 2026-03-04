# 股票量化自动化系统 - 完整使用指南

## 系统概述

本系统是一套完整的股票量化自动化解决方案，包含数据管理、定时调度、选股、回测、复盘和通知功能。

### 核心功能

1. **数据统一管理**：SQLite数据库，增量更新，历史保留
2. **定时任务调度**：15:30/16:00/18:00/20:00/21:00自动执行
3. **尾盘选股**：基于技术指标和资金流向筛选次日买入标的
4. **历史回测**：验证策略有效性，输出核心指标
5. **市场复盘**：分析涨跌分布、热门板块、资金流向
6. **自动通知**：通过豆包API推送结果

---

## 第一步：现有程序清单

### 已有程序

| 程序文件 | 功能 | 状态 |
|:---|:---|:---|
| `scripts/evening_stock_selector_v2.py` | 尾盘选股（次日早盘买入）| ✅ 已优化 |
| `scripts/market_review.py` | 市场复盘 | ✅ 可用 |
| `scripts/strategy_backtest_optimized.py` | 策略回测 | ✅ 可用 |
| `scripts/auto_data_downloader.py` | 数据下载 | ✅ 可用 |
| `scripts/unified_scheduler.py` | 统一调度 | ✅ 可用 |

### 新增程序

| 程序文件 | 功能 | 状态 |
|:---|:---|:---|
| `src/data/data_manager.py` | 数据统一管理（SQLite）| ✅ 新增 |
| `src/scheduler/auto_scheduler.py` | 自动化定时调度 | ✅ 新增 |
| `src/notification/notification_sender.py` | 豆包API通知 | ✅ 新增 |
| `main.py` | 系统主入口 | ✅ 新增 |

---

## 第二步：完整自动化系统代码

### 系统架构

```
股票量化自动化系统
├── main.py                          # 主入口
├── src/
│   ├── data/
│   │   └── data_manager.py       # 数据统一管理
│   ├── scheduler/
│   │   └── auto_scheduler.py      # 定时调度
│   └── notification/
│       └── notification_sender.py   # 通知发送
├── scripts/
│   ├── evening_stock_selector_v2.py # 尾盘选股
│   ├── market_review.py            # 市场复盘
│   ├── strategy_backtest_optimized.py # 策略回测
│   └── auto_data_downloader.py    # 数据下载
├── data/
│   └── stock_data.db             # SQLite数据库
├── logs/                          # 日志目录
└── .env                           # 配置文件
```

### 核心模块说明

#### 1. 数据管理模块（`src/data/data_manager.py`）

**核心功能**：
- SQLite数据库统一管理所有数据
- 支持增量更新，避免重复下载
- 提供统一的数据查询接口
- 自动数据校验和清理

**主要方法**：
```python
# 保存股票日线数据
save_stock_daily(df: pd.DataFrame) -> Dict

# 获取股票日线数据
get_stock_daily(code=None, start_date=None, end_date=None, limit=None) -> pd.DataFrame

# 保存因子数据
save_factor_data(df: pd.DataFrame) -> Dict

# 保存选股结果
save_selection_results(df: pd.DataFrame, date: str) -> Dict

# 保存回测结果
save_backtest_results(results: Dict, date: str) -> Dict

# 保存复盘数据
save_review_data(review: Dict, date: str) -> Dict
```

#### 2. 定时调度模块（`src/scheduler/auto_scheduler.py`）

**核心功能**：
- 统一管理所有定时任务
- 按时间顺序执行任务
- 任务依赖管理
- 错误重试机制
- 自动发送通知

**定时任务配置**：
```python
tasks = {
    'data_download': {
        'time': '15:30',
        'name': '数据下载',
        'enabled': True
    },
    'factor_calculation': {
        'time': '16:00',
        'name': '因子计算',
        'enabled': True
    },
    'stock_selection': {
        'time': '18:00',
        'name': '尾盘选股',
        'enabled': True
    },
    'backtest': {
        'time': '20:00',
        'name': '历史回测',
        'enabled': True
    },
    'market_review': {
        'time': '21:00',
        'name': '市场复盘',
        'enabled': True
    }
}
```

**任务依赖关系**：
- `factor_calculation` 依赖 `data_download`
- `stock_selection` 依赖 `data_download` 和 `factor_calculation`
- `backtest` 依赖 `stock_selection`
- `market_review` 依赖 `data_download`

#### 3. 通知发送模块（`src/notification/notification_sender.py`）

**核心功能**：
- 通过豆包API发送通知
- 结构化消息格式
- 高亮显示关键信息
- 自动重试机制

**通知内容格式**：
```
【任务名称】
时间: 2026-03-03 18:00:00
任务执行结果

详细信息：
📊 选股结果：
  1. 600XXX 股票名称
     收盘: 18.50元  涨幅: +3.50%
     得分: 85分  逻辑: 涨幅适中(3-5%), 换手健康(3-10%)
     买入: 18.40-18.60元
     止损: 17.95元  止盈: 19.43元

📈 回测结果：
  总交易: 20次
  胜率: 65.00%
  年化收益: 25.50%
  最大回撤: 15.00%
  夏普比率: 1.70
  盈亏比: 2.50

📋 市场复盘：
  上涨: 331只
  下跌: 1923只
  平盘: 18只
  平均涨跌: -2.49%
  成交额: 14666.55亿元
  热门板块: 农业, 金融, 新能源
  市场情绪: 弱势
  交易建议: 观望为主
```

---

## 第三步：定时任务配置说明

### 启动方式

#### 方式1：自动调度模式（推荐）

```bash
# 启动自动调度系统
python main.py --mode schedule
```

**说明**：
- 系统将按配置的时间自动执行任务
- 按 Ctrl+C 停止系统
- 适合长期运行的服务器环境

#### 方式2：手动执行模式

```bash
# 执行所有任务
python main.py --mode manual --task all

# 执行单个任务
python main.py --mode manual --task data      # 数据下载
python main.py --mode manual --task factor    # 因子计算
python main.py --mode manual --task selection # 尾盘选股
python main.py --mode manual --task backtest  # 历史回测
python main.py --mode manual --task review   # 市场复盘
```

#### 方式3：查看系统信息

```bash
# 查看系统信息
python main.py --mode info
```

#### 方式4：清理旧数据

```bash
# 清理365天前的旧数据
python main.py --mode cleanup --cleanup-days 365
```

### 修改定时任务时间

编辑 `src/scheduler/auto_scheduler.py` 中的任务配置：

```python
self.tasks = {
    'data_download': {
        'time': '15:30',  # 修改这里
        'name': '数据下载',
        'enabled': True    # 设置为False禁用
    },
    # ... 其他任务
}
```

### 修改任务依赖关系

编辑 `check_dependencies` 方法：

```python
dependencies = {
    'factor_calculation': ['data_download'],
    'stock_selection': ['data_download', 'factor_calculation'],
    'backtest': ['stock_selection'],
    'market_review': ['data_download']
    # ... 修改依赖关系
}
```

---

## 第四步：所需资源清单

### 已有资源

| 资源 | 配置项 | 状态 | 说明 |
|:---|:---|:---|:---|
| Tushare Token | `TUSHARE_TOKEN` | ⚠️ 未配置 | 需要配置 |
| 豆包API Key | `DOUBAO_API_KEY` | ⚠️ 未配置 | 需要配置 |
| 数据源配置 | `DATA_SOURCE_PRIORITY` | ✅ 已配置 | akshare,efinance,tushare |
| 缓存配置 | `DATA_CACHE_ENABLED` | ✅ 已配置 | true |
| 策略配置 | `STRATEGY_*` | ✅ 已配置 | 价格、换手率、止损等 |
| 定时配置 | `SCHEDULE_*` | ✅ 已配置 | 时间、日期等 |

### 需要补充的资源

#### 1. Tushare Token（必需）

**用途**：首选数据源，提供完整的历史数据

**获取方式**：
1. 访问 https://tushare.pro/register
2. 注册账号
3. 获取API Token
4. 配置到 `.env` 文件

**配置示例**：
```env
TUSHARE_TOKEN=your_actual_token_here
```

#### 2. 豆包API Key（必需）

**用途**：发送任务结果通知

**获取方式**：
1. 访问 https://console.volcengine.com/ark
2. 创建应用并获取API Key
3. 配置到 `.env` 文件

**配置示例**：
```env
DOUBAO_API_KEY=your_actual_api_key_here
DOUBAO_MODEL=Doubao-Seedream-5.0-lite
DOUBAO_API_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions
DOUBAO_MAX_TOKENS=1000
DOUBAO_TEMPERATURE=0.7
DOUBAO_PUSH_ENABLED=true
```

#### 3. Python依赖库（需要安装）

```bash
# 核心依赖
pip install pandas numpy sqlite3

# 数据源
pip install akshare tushare efinance

# 调度
pip install schedule

# 通知
pip install requests python-dotenv

# 可视化（可选）
pip install matplotlib seaborn
```

#### 4. 系统要求

- Python 3.10+
- 稳定网络连接
- 足够磁盘空间（用于存储历史数据）

### 配置文件说明

#### `.env` 文件完整配置

```env
# ===================================
# 数据源配置
# ===================================
DATA_SOURCE_PRIORITY=akshare,efinance,tushare
DATA_CACHE_ENABLED=true
DATA_CACHE_TTL_HOURS=1

# Tushare API Token
TUSHARE_TOKEN=your_tushare_token_here

# ===================================
# 豆包API配置
# ===================================
DOUBAO_API_KEY=your_doubao_api_key_here
DOUBAO_MODEL=Doubao-Seedream-5.0-lite
DOUBAO_API_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions
DOUBAO_MAX_TOKENS=1000
DOUBAO_TEMPERATURE=0.7
DOUBAO_PUSH_ENABLED=true
DOUBAO_RETRY_TIMES=3
DOUBAO_RETRY_DELAY=5

# ===================================
# 策略配置
# ===================================
STRATEGY_PRICE_MIN=5.0
STRATEGY_PRICE_MAX=35.0
STRATEGY_TURNOVER_RATE_MIN=3.0
STRATEGY_TURNOVER_RATE_MAX=10.0
STRATEGY_VOLUME_RATIO_THRESHOLD=1.5
STRATEGY_HOLD_DAYS=2
STRATEGY_STOP_LOSS_PERCENT=3.0

# ===================================
# 定时任务配置
# ===================================
SCHEDULE_ENABLED=true
SCHEDULE_DATA_DOWNLOAD_TIMES=15:30
SCHEDULE_SELECTION_TIME=18:00
SCHEDULE_BACKTEST_TIME=20:00
SCHEDULE_REVIEW_TIME=21:00

# ===================================
# 日志配置
# ===================================
LOG_LEVEL=INFO
LOG_DIR=logs
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5

# ===================================
# 其他配置
# ===================================
ENVIRONMENT=production
TIMEZONE=Asia/Shanghai
```

---

## 系统使用流程

### 首次使用

1. **配置环境变量**
   ```bash
   # 复制配置模板
   cp .env.example .env
   
   # 编辑配置文件，填入API密钥
   notepad .env
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **初始化数据库**
   ```bash
   # 首次运行会自动创建数据库
   python main.py --mode info
   ```

4. **启动系统**
   ```bash
   # 自动调度模式
   python main.py --mode schedule
   ```

### 日常使用

#### 自动运行（推荐）

```bash
# 启动自动调度系统
python main.py --mode schedule
```

系统将自动在以下时间执行任务：
- 15:30 - 数据下载
- 16:00 - 因子计算
- 18:00 - 尾盘选股
- 20:00 - 历史回测
- 21:00 - 市场复盘

#### 手动执行

```bash
# 手动执行所有任务
python main.py --mode manual --task all

# 手动执行单个任务
python main.py --mode manual --task selection
```

#### 查看信息

```bash
# 查看系统信息
python main.py --mode info
```

#### 清理数据

```bash
# 清理365天前的旧数据
python main.py --mode cleanup --cleanup-days 365
```

---

## 数据管理说明

### 数据库结构

#### stock_daily（股票日线数据）
```sql
CREATE TABLE stock_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,              -- 股票代码
    name TEXT,                        -- 股票名称
    date TEXT NOT NULL,               -- 日期
    open REAL,                        -- 开盘价
    high REAL,                        -- 最高价
    low REAL,                         -- 最低价
    close REAL,                       -- 收盘价
    volume REAL,                      -- 成交量
    amount REAL,                       -- 成交额
    pct_chg REAL,                     -- 涨跌幅
    turnover REAL,                    -- 换手率
    volume_ratio REAL,                 -- 量比
    circ_mv REAL,                     -- 流通市值
    total_mv REAL,                    -- 总市值
    amplitude REAL,                   -- 振幅
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(code, date)
);
```

#### factor_data（因子数据）
```sql
CREATE TABLE factor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,               -- 股票代码
    date TEXT NOT NULL,               -- 日期
    ma5 REAL,                        -- MA5
    ma10 REAL,                       -- MA10
    ma20 REAL,                       -- MA20
    ma60 REAL,                       -- MA60
    macd_dif REAL,                   -- MACD DIF
    macd_dea REAL,                   -- MACD DEA
    macd_hist REAL,                  -- MACD柱
    rsi REAL,                        -- RSI
    boll_up REAL,                     -- 布林带上轨
    boll_mid REAL,                    -- 布林带中轨
    boll_down REAL,                   -- 布林带下轨
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(code, date)
);
```

#### selection_results（选股结果）
```sql
CREATE TABLE selection_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,               -- 选股日期
    code TEXT NOT NULL,               -- 股票代码
    name TEXT,                        -- 股票名称
    close REAL,                       -- 收盘价
    pct_chg REAL,                     -- 涨跌幅
    turnover REAL,                    -- 换手率
    volume_ratio REAL,                 -- 量比
    circ_mv REAL,                     -- 流通市值
    selection_score INTEGER,            -- 综合得分
    selection_logic TEXT,              -- 入选逻辑
    buy_range TEXT,                   -- 买入区间
    stop_loss REAL,                   -- 止损位
    take_profit REAL,                  -- 止盈位
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### backtest_results（回测结果）
```sql
CREATE TABLE backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,               -- 回测日期
    strategy_name TEXT,                -- 策略名称
    total_trades INTEGER,             -- 总交易次数
    win_trades INTEGER,               -- 盈利次数
    loss_trades INTEGER,              -- 亏损次数
    win_rate REAL,                    -- 胜率
    total_return REAL,                 -- 总收益
    annualized_return REAL,            -- 年化收益
    max_drawdown REAL,                 -- 最大回撤
    sharpe_ratio REAL,                -- 夏普比率
    profit_loss_ratio REAL,             -- 盈亏比
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### review_data（复盘数据）
```sql
CREATE TABLE review_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,               -- 复盘日期
    up_count INTEGER,                 -- 上涨数量
    down_count INTEGER,                -- 下跌数量
    flat_count INTEGER,                -- 平盘数量
    avg_pct_chg REAL,                 -- 平均涨跌幅
    total_amount REAL,                 -- 总成交额
    hot_sectors TEXT,                 -- 热门板块
    capital_flow REAL,                 -- 资金流向
    limit_up_count INTEGER,            -- 涨停数量
    limit_down_count INTEGER,           -- 跌停数量
    market_sentiment TEXT,             -- 市场情绪
    trading_advice TEXT,               -- 交易建议
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date)
);
```

### 数据更新策略

1. **增量更新**：仅下载当日新数据
2. **历史保留**：保留所有历史数据
3. **自动去重**：使用UNIQUE约束避免重复
4. **定期清理**：支持清理N天前的旧数据

---

## 通知说明

### 通知触发时机

1. **任务完成**：每个定时任务完成后立即发送
2. **任务失败**：任务执行失败时发送错误通知
3. **执行汇总**：所有任务完成后发送汇总通知

### 通知内容

通知包含以下信息：
- 任务名称和执行时间
- 执行结果（成功/失败）
- 关键数据（选股清单、回测指标、复盘数据）
- 错误信息（如有）

### 通知格式

```
【股票量化系统 - 任务名称】
时间: 2026-03-03 18:00:00
任务执行结果

详细信息：
📊 选股结果：
  [股票列表]

📈 回测结果：
  [回测指标]

📋 市场复盘：
  [复盘数据]

⚠️ 免责声明：以上内容仅供参考，不构成投资建议
```

---

## 日志说明

### 日志文件

| 日志文件 | 说明 |
|:---|:---|
| `logs/main.log` | 主程序日志 |
| `logs/auto_scheduler.log` | 调度器日志 |
| `logs/data_manager.log` | 数据管理器日志 |
| `logs/notification.log` | 通知发送日志 |
| `logs/evening_selector.log` | 尾盘选股日志 |
| `logs/market_review.log` | 市场复盘日志 |

### 日志级别

- `DEBUG`：详细调试信息
- `INFO`：一般信息（默认）
- `WARNING`：警告信息
- `ERROR`：错误信息
- `CRITICAL`：严重错误

---

## 常见问题

### Q1: 如何修改定时任务时间？

A: 编辑 `src/scheduler/auto_scheduler.py` 中的 `self.tasks` 配置，修改 `time` 字段。

### Q2: 如何禁用某个定时任务？

A: 编辑 `src/scheduler/auto_scheduler.py`，将对应任务的 `enabled` 设置为 `False`。

### Q3: 如何查看历史选股结果？

A: 使用数据管理器查询：
```python
from src.data.data_manager import get_data_manager
dm = get_data_manager()
results = dm.get_selection_results(date='2026-03-03')
print(results)
```

### Q4: 如何清理旧数据？

A: 运行清理命令：
```bash
python main.py --mode cleanup --cleanup-days 365
```

### Q5: 通知发送失败怎么办？

A: 检查以下配置：
1. `.env` 文件中 `DOUBAO_API_KEY` 是否正确
2. `DOUBAO_PUSH_ENABLED` 是否设置为 `true`
3. 网络连接是否正常
4. 查看 `logs/notification.log` 了解详细错误信息

### Q6: 数据下载失败怎么办？

A: 系统会自动切换数据源：
1. 首选 Tushare（需要配置Token）
2. 备用 Akshare-东方财富（数据完整）
3. 备用 Akshare-新浪财经（基础数据）

### Q7: 如何查看系统运行状态？

A: 运行信息命令：
```bash
python main.py --mode info
```

---

## 技术支持

### 联系方式

- 查看日志文件了解详细错误信息
- 检查配置文件是否正确
- 确认网络连接正常

### 版本信息

- 系统版本：v1.0
- Python版本：3.10+
- 数据库：SQLite 3.x

---

## 免责声明

本系统提供的所有信息（包括选股结果、回测指标、复盘数据、交易建议等）仅供参考，不构成任何投资建议。股市有风险，投资需谨慎。使用本系统所造成的任何损失，开发者不承担责任。

---

**最后更新时间**：2026-03-03
**文档版本**：v1.0
