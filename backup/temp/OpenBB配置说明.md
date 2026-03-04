# OpenBB数据源配置说明

## 一、环境配置

### 1.1 Python版本
- **主版本**: Python 3.11.9（兼容OpenBB v4.1.0）
- **安装路径**: `C:\Users\Administrator\AppData\Local\Programs\Python\Python311\`
- **虚拟环境**: `.venv`（位于项目根目录）

### 1.2 虚拟环境
```bash
# 激活虚拟环境
.venv\Scripts\activate.bat

# 验证Python版本
python --version  # 应显示 Python 3.11.9
```

### 1.3 已安装核心依赖
```
openbb==4.1.0
openbb-core==1.6.0
pandas==2.1.4
tushare==1.4.25
akshare==1.18.32
tenacity==9.1.4
```

## 二、核心调用函数

### 2.1 统一数据获取接口

```python
from src.openbb_data import get_openbb_stock_data

# 获取股票数据
data, source = get_openbb_stock_data(
    symbol="000001.SZ",           # 股票代码
    start_date="2024-01-01",      # 开始日期（可选）
    end_date="2024-12-31",        # 结束日期（可选）
    interval="1d"                 # 数据间隔：1d=日线, 1h=小时线
)

# 返回值
# data: pandas.DataFrame（标准化后的数据）
# source: 数据源名称（openbb/tushare/akshare/cache）
```

### 2.2 数据字段说明

获取的数据包含以下标准化字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| trade_date | str | 交易日期（YYYY-MM-DD） |
| open | float | 开盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| close | float | 收盘价 |
| volume | float | 成交量 |

### 2.3 数据校验

```python
from src.openbb_data.data_validator import validate_stock_data

# 校验数据
is_valid, fixed_data, result = validate_stock_data(
    df=data,
    symbol="000001.SZ",
    auto_fix=True  # 自动修复常见问题
)

# 查看校验结果
print(f"校验通过: {is_valid}")
print(f"质量分数: {result.data_quality_score}")
print(f"错误数: {len(result.errors)}")
print(f"警告数: {len(result.warnings)}")
```

## 三、数据源优先级

### 3.1 优先级顺序

```
1. OpenBB（主数据源）
   ↓（失败/超时/数据异常）
2. Tushare（备用1）
   ↓（失败/无token）
3. AkShare（备用2）
   ↓（失败/网络错误）
4. 本地SQLite缓存（最终兜底）
```

### 3.2 切换触发条件

| 条件类型 | 触发行为 |
|----------|----------|
| 数据源超时（20秒） | 自动切换到下一级数据源 |
| 数据字段缺失 | 标记为失败，尝试下一级 |
| 数值异常（如涨跌幅>10%） | 标记为失败，尝试下一级 |
| 网络连接错误 | 重试3次后切换 |
| API返回错误 | 立即切换 |

### 3.3 重试配置

```python
retry_config = {
    'max_retries': 3,              # 最大重试次数
    'retry_intervals': [3, 8, 15], # 重试间隔（秒）
    'timeout': 20                  # 请求超时（秒）
}
```

## 四、异常处理流程

### 4.1 数据获取异常

```
1. 尝试从OpenBB获取
   ├─ 成功 → 数据校验 → 返回数据
   └─ 失败 → 记录日志 → 等待3秒 → 重试
      ├─ 3次重试后仍失败 → 切换到Tushare
      └─ 切换时发送告警通知

2. 尝试从Tushare获取
   ├─ 成功 → 数据校验 → 返回数据
   └─ 失败 → 记录日志 → 等待3秒 → 重试
      └─ 3次重试后仍失败 → 切换到AkShare

3. 尝试从AkShare获取
   ├─ 成功 → 数据校验 → 返回数据
   └─ 失败 → 记录日志 → 等待3秒 → 重试
      └─ 3次重试后仍失败 → 切换到本地缓存

4. 尝试从本地缓存获取
   ├─ 成功 → 返回缓存数据
   └─ 失败 → 返回None，记录错误
```

### 4.2 数据校验异常

```python
# 自动修复的常见问题：
1. 删除重复日期记录
2. 使用前向填充处理空值
3. 将负成交量修正为0
4. 修正价格逻辑错误（确保low <= close <= high）
```

### 4.3 通知机制

每次数据源切换时，会自动发送通知到豆包：

```python
{
    "title": "数据源切换告警",
    "message": "从OpenBB切换到Tushare",
    "reason": "代码层面问题：请求超时" / "数据源层面问题：返回数据为空",
    "timestamp": "2024-01-01 12:00:00"
}
```

## 五、目录结构

```
daily_stock_analysis/
├── .venv/                          # Python 3.11.9 虚拟环境
│   └── Scripts/
│       └── python.exe              # 解释器路径
├── src/
│   └── openbb_data/                # OpenBB数据模块
│       ├── __init__.py
│       ├── openbb_fetcher.py       # 数据获取核心
│       └── data_validator.py       # 数据校验
├── data/
│   └── stock_data.db               # 本地SQLite缓存
├── openbb_deps/
│   └── requirements_openbb.txt     # OpenBB依赖清单
├── .vscode/
│   └── settings.json               # VS Code配置
├── scripts/
│   └── test_openbb_reliability.py  # 可靠性测试脚本
└── OpenBB双层面可靠性测试报告.md    # 测试报告
```

## 六、手动验证命令

### 6.1 验证GitHub代码可用性

```bash
# 测试OpenBB导入
.venv\Scripts\python.exe -c "from openbb import obb; print('✅ OpenBB可用')"

# 测试OpenBB功能
.venv\Scripts\python.exe -c "from openbb import obb; output = obb.equity.price.historical('AAPL', limit=5); print(f'✅ 获取{len(output.to_dataframe())}条数据')"
```

### 6.2 验证OpenBB数据源可用性

```bash
# 测试自定义模块
.venv\Scripts\python.exe -c "from src.openbb_data import get_openbb_stock_data; data, source = get_openbb_stock_data('000001.SZ'); print(f'✅ 数据源: {source}, 数据条数: {len(data) if data is not None else 0}')"
```

### 6.3 运行完整测试

```bash
# 运行4场景可靠性测试
.venv\Scripts\python.exe scripts\test_openbb_reliability.py
```

## 七、故障排查

### 7.1 OpenBB导入失败

**现象**: `ModuleNotFoundError: No module named 'openbb'`

**解决**:
```bash
# 确保在虚拟环境中
.venv\Scripts\activate.bat

# 重新安装OpenBB
pip install openbb==4.1.0
```

### 7.2 数据源全部失败

**现象**: 所有数据源都返回None

**排查步骤**:
1. 检查网络连接
2. 检查Tushare token是否配置
3. 检查本地缓存是否存在
4. 查看日志文件 `openbb_test.log`

### 7.3 VS Code解释器错误

**现象**: VS Code提示Python解释器路径错误

**解决**:
1. 按 `Ctrl+Shift+P`
2. 输入 `Python: Select Interpreter`
3. 选择 `./.venv/Scripts/python.exe`

## 八、配置总结

| 配置项 | 值 | 说明 |
|--------|-----|------|
| Python版本 | 3.11.9 | 兼容OpenBB v4.1.0 |
| OpenBB版本 | 4.1.0 | 稳定版本 |
| 请求超时 | 20秒 | 防止长时间等待 |
| 重试次数 | 3次 | 梯度间隔3/8/15秒 |
| 数据源优先级 | OpenBB→Tushare→AkShare→缓存 | 自动切换 |
| 数据校验 | 启用 | 字段完整性+数值合理性 |
| 本地缓存 | SQLite | 最终兜底方案 |

---

*文档生成时间: 2026-03-04*
