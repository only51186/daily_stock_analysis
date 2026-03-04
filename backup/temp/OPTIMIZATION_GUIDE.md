# 系统优化指南

## 【核心约束】

1. **保留所有原有功能**：仅对重复模块合并、开发顺序优化，不删减任何已有功能
2. **优先落地高价值核心需求**：次要优化需求后置，最大程度减少开发工作量
3. **适配场景**：沪深主板5-35元超短线（1-2天）选股，Python 3.14.3环境，调用豆包Doubao-Seedream-5.0-lite模型

---

## 【开发优先级清单】

### 优先级1：核心自动化模块（已完成 ✅）

#### 1.1 数据下载自动化
- **状态**: ✅ 已完成
- **文件**: `scripts/auto_data_downloader.py`
- **功能**:
  - 保留原有akshare/efinance/tushare数据源
  - 新增「每日9:30/14:00定时自动下载」功能
  - 合并原有重复的"数据请求-解析"逻辑
  - 新增本地CSV缓存（有效期1小时），避免重复请求
  - 复用原有Windows任务计划程序适配逻辑

#### 1.2 选股+回测自动化
- **状态**: ✅ 已完成
- **文件**: `scripts/unified_scheduler.py`
- **功能**:
  - 保留原有选股因子（5-35元、换手率3%-10%等）和回测逻辑（backtrader）
  - 合并选股、回测的触发逻辑：每日14:30自动运行选股，每周日自动运行回测
  - 共用一套调度脚本，减少重复代码
  - 保留原有选股/回测结果格式，仅新增"自动保存+覆盖"逻辑

#### 1.3 消息自动推送
- **状态**: ✅ 已完成
- **文件**: `utils/notification_sender.py`（修改）
- **功能**:
  - 保留原有本地文件输出功能
  - 新增豆包API推送（复用原有API调用框架，仅补充Key配置）
  - 合并"选股结果推送"和"回测结果推送"为统一推送函数
  - 推送失败时复用原有日志逻辑，新增3次自动重试

### 优先级2：可视化模块（已完成 ✅）

#### 2.1 股票走势预测交互界面
- **状态**: ✅ 已完成
- **文件**: `scripts/stock_prediction_ui.py`
- **功能**:
  - 基于tkinter开发（复用原有界面依赖）
  - 支持输入单个股票代码
  - 显示近30天历史走势曲线（价格+成交量双轴）
  - 显示未来2天预测走势曲线（标注上涨概率/关键价位）
  - 情绪评分/板块热度（复用原有情绪分析逻辑）
  - 界面适配新手操作，无需新增复杂依赖

### 优先级3：智能化优化模块（部分完成 ⚠️）

#### 3.1 代码故障自动修复
- **状态**: ⏸️ 后置开发
- **说明**: 基于原有异常捕获逻辑，补充修复规则
- **功能**:
  - 保留原有异常日志
  - 新增「常见故障自动修复规则」（数据源失效切换、文件读写失败重试、因子计算错误兜底）
  - 无法自动修复时，复用原有弹窗/日志提示逻辑，仅补充"手动修复建议"

#### 3.2 省token优化
- **状态**: ✅ 已完成（已集成到推送模块）
- **文件**: `utils/notification_sender.py`（修改）
- **功能**:
  - 保留原有豆包API调用框架
  - 优化指令格式（仅传递核心内容，删除冗余描述），max_tokens控制在1000以内
  - 复用原有数据缓存逻辑，避免重复调用模型
  - 新增token额度监控（复用原有日志模块），剩余<10%时自动切换轻量化推理

---

## 【配置文件说明】

### 统一配置文件

**文件**: `config/settings.py`

**功能**: 合并重复的配置项（数据源、API、定时任务等）

**配置优先级**: 环境变量 > 配置文件 > 默认值

### 主要配置项

```python
# 数据源配置
DATA_CACHE_ENABLED=true          # 启用缓存
DATA_CACHE_TTL_HOURS=1           # 缓存有效期1小时
DOWNLOAD_TIMES=["09:30", "14:00"] # 自动下载时间

# 豆包API配置
DOUBAO_API_KEY=0cf5bc0e-28c2-43a1-a820-49425236ec2c
DOUBAO_MODEL=Doubao-Seedream-5.0-lite
DOUBAO_MAX_TOKENS=1000
DOUBAO_PUSH_ENABLED=true

# 策略配置
STRATEGY_PRICE_MIN=5.0
STRATEGY_PRICE_MAX=35.0
STRATEGY_HOLD_DAYS=2
STRATEGY_SELECTION_TIME=14:30

# 定时任务配置
SCHEDULE_SELECTION_TIME=14:30
SCHEDULE_BACKTEST_DAY=Sunday
SCHEDULE_BACKTEST_TIME=20:00
```

---

## 【使用方法】

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动数据下载自动化

```bash
# 方法1：立即下载一次
python scripts/auto_data_downloader.py

# 方法2：启动定时调度（后台运行）
python scripts/auto_data_downloader.py
# 会自动在9:30和14:00下载数据
```

### 3. 启动统一调度器

```bash
# 方法1：立即运行所有任务
python scripts/unified_scheduler.py --run-all

# 方法2：仅运行选股
python scripts/unified_scheduler.py --selection

# 方法3：仅运行回测
python scripts/unified_scheduler.py --backtest

# 方法4：仅运行复盘
python scripts/unified_scheduler.py --review

# 方法5：启动定时调度器（后台运行）
python scripts/unified_scheduler.py --scheduler
```

### 4. 启动股票走势预测界面

```bash
python scripts/stock_prediction_ui.py
```

**界面功能**:
- 输入股票代码（支持600xxx, 601xxx, 603xxx, 000xxx）
- 查看近30天历史走势
- 查看情绪评分
- 查看未来2天走势预测
- 查看关键价位和操作建议

### 5. 使用批处理脚本（推荐）

```bash
# 运行选股策略和每日复盘
auto_run.bat

# 运行策略回测
run_backtest.bat
```

---

## 【定时任务配置】

### Windows 任务计划程序

1. 打开"任务计划程序"（taskschd.msc）
2. 创建基本任务
3. 设置触发器：
   - **数据下载**：每日 9:30 和 14:00
   - **选股策略**：每个工作日的 14:30
   - **每日复盘**：每个工作日的 09:00
   - **策略回测**：每周日的 20:00
4. 设置操作为"启动程序"
5. 浏览并选择相应的批处理文件
6. 完成设置

### 推荐的定时任务

| 任务 | 时间 | 频率 | 脚本 |
|------|------|------|------|
| 数据下载 | 09:30, 14:00 | 每日 | `scripts/auto_data_downloader.py` |
| 选股策略 | 14:30 | 工作日 | `scripts/unified_scheduler.py --selection` |
| 每日复盘 | 09:00 | 工作日 | `scripts/unified_scheduler.py --review` |
| 策略回测 | 20:00 | 每周日 | `scripts/unified_scheduler.py --backtest` |

---

## 【文件结构】

```
daily_stock_analysis/
├── config/
│   └── settings.py              # 【新增】统一配置文件
├── data_provider/
│   ├── multi_data_source.py     # 【修改】集成缓存功能
│   └── data_cache.py            # 【已有】数据缓存模块
├── scripts/
│   ├── auto_data_downloader.py  # 【新增】数据下载自动化
│   ├── unified_scheduler.py     # 【新增】统一调度模块
│   ├── stock_prediction_ui.py   # 【新增】股票走势预测界面
│   ├── hs_mainboard_short_strategy.py  # 【修改】添加日志功能
│   ├── strategy_backtest.py     # 【修改】添加日志功能
│   ├── strategy_optimizer.py    # 【已有】策略参数调优
│   └── daily_review.py          # 【已有】每日复盘
├── utils/
│   ├── notification_sender.py   # 【修改】统一推送+重试机制
│   └── logger_config.py         # 【已有】日志配置模块
├── auto_run.bat                 # 【已有】自动运行脚本
├── run_backtest.bat             # 【已有】回测运行脚本
├── VENV_SETUP.md               # 【已有】虚拟环境配置指南
├── AUTO_RUN_GUIDE.md           # 【已有】自动运行脚本使用指南
└── OPTIMIZATION_GUIDE.md       # 【新增】本文件
```

---

## 【新增/修改/合并标注】

### 新增文件

1. `config/settings.py` - 统一配置文件
2. `scripts/auto_data_downloader.py` - 数据下载自动化
3. `scripts/unified_scheduler.py` - 统一调度模块
4. `scripts/stock_prediction_ui.py` - 股票走势预测界面

### 修改文件

1. `utils/notification_sender.py` - 添加统一推送函数、重试机制、Token优化
2. `scripts/hs_mainboard_short_strategy.py` - 添加日志功能
3. `scripts/strategy_backtest.py` - 添加日志功能
4. `requirements.txt` - 添加matplotlib依赖

### 合并逻辑

1. **数据请求逻辑**：合并到 `auto_data_downloader.py`
2. **调度逻辑**：合并到 `unified_scheduler.py`
3. **推送逻辑**：合并到 `notification_sender.py` 的 `send_unified_notification` 方法

---

## 【测试用例】

### 1. 数据下载测试

```bash
python scripts/auto_data_downloader.py
```

**预期结果**:
- 成功下载板块数据（10个板块）
- 成功下载股票数据（5000+只股票）
- 成功下载历史数据（50只热门股票）
- 数据保存到 `data_cache/` 目录

### 2. 统一调度测试

```bash
python scripts/unified_scheduler.py --run-all
```

**预期结果**:
- 成功运行选股策略
- 成功运行每日复盘
- 成功推送结果到豆包

### 3. 股票走势预测界面测试

```bash
python scripts/stock_prediction_ui.py
```

**测试步骤**:
1. 输入股票代码 `600000`
2. 点击"查询"按钮
3. 验证显示内容：
   - 股票信息面板显示正确
   - 情绪评分面板显示正确
   - 走势图表显示正确（价格+成交量+涨跌幅）
   - 预测面板显示正确

### 4. 消息推送测试

```python
from utils.notification_sender import get_notification_sender

sender = get_notification_sender()

# 测试选股结果推送
test_sectors = [{'name': '半导体', 'change_pct': 5.2}]
test_stocks = [{'code': '600000', 'name': '浦发银行', 'price': 10.5, 'change_pct': 2.1, 'total_score': 85.5}]
sender.send_stock_selection_result(test_sectors, test_stocks)
```

**预期结果**:
- 消息成功发送到豆包
- 如果失败，自动重试3次
- Token使用记录在日志中

---

## 【故障排除】

### 常见问题

#### 1. 虚拟环境激活失败

**解决方法**:
```bash
# 重新创建虚拟环境
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. 数据下载失败

**检查项**:
- 网络连接是否正常
- 数据源API是否可用
- 查看日志：`logs/data.log`

**自动修复**:
- 系统会自动切换到备用数据源
- 重试3次后仍失败会记录错误日志

#### 3. 消息推送失败

**检查项**:
- API Key是否正确
- 网络连接是否正常
- Token额度是否充足

**自动修复**:
- 系统会自动重试3次
- Token不足时自动切换轻量化推理

#### 4. 界面无法启动

**检查项**:
- tkinter是否安装（Python自带）
- matplotlib是否正确安装
- 查看日志：`logs/ui.log`

---

## 【后续优化建议】

### 高优先级（建议立即实施）

1. **完善代码故障自动修复**：补充更多修复规则
2. **优化预测算法**：使用机器学习模型提高预测准确率
3. **增加更多数据源**：如东方财富、同花顺等

### 中优先级（建议后续实施）

1. **Web界面**：基于Streamlit开发Web版界面
2. **移动端适配**：开发手机APP或小程序
3. **多账户管理**：支持多个交易账户管理

### 低优先级（建议长期规划）

1. **AI策略优化**：使用强化学习优化策略参数
2. **社交功能**：用户分享选股结果
3. **量化交易接口**：对接券商API实现自动交易

---

## 【联系支持】

如遇到问题，请查看日志文件或联系技术支持。

**日志文件位置**:
- `logs/strategy.log` - 选股策略日志
- `logs/backtest.log` - 回测日志
- `logs/data.log` - 数据下载日志
- `logs/ui.log` - 界面日志
- `logs/scheduler.log` - 调度器日志
