# OpenBB数据源配置说明

## 1. 依赖清单

### 核心依赖
- Python 3.10+
- OpenBB：`pip install openbb`
- 其他依赖：
  - pandas
  - akshare
  - efinance
  - requests
  - sqlite3

### 安装步骤
1. 安装OpenBB：`pip install openbb`
2. 安装其他依赖：`pip install -r requirements.txt`

## 2. 核心调用函数

### 数据源优先级
- **主数据源**：OpenBB
- **备用数据源**：
  1. Akshare
  2. Efinance
  3. Eastmoney（东方财富网爬虫）
- **兜底**：本地缓存

### 主要函数

#### 1. `get_multi_data_source()`
- **功能**：获取多数据源实例（单例模式）
- **返回**：`MultiDataSource`实例

#### 2. `get_sector_rankings(n=10, use_cache=True)`
- **功能**：获取板块热度排名
- **参数**：
  - `n`：返回前N个板块
  - `use_cache`：是否使用缓存
- **返回**：`(板块列表, 数据源名称)`

#### 3. `get_all_stocks(use_cache=True)`
- **功能**：获取所有A股股票数据
- **参数**：
  - `use_cache`：是否使用缓存
- **返回**：`(股票数据DataFrame, 数据源名称)`

#### 4. `get_stock_daily_data(code, days=30, use_cache=True)`
- **功能**：获取个股历史数据
- **参数**：
  - `code`：股票代码
  - `days`：获取天数
  - `use_cache`：是否使用缓存
- **返回**：`(历史数据DataFrame, 数据源名称)`

#### 5. `get_realtime_data(codes)`
- **功能**：获取实时行情数据
- **参数**：
  - `codes`：股票代码列表
- **返回**：`(实时数据DataFrame, 数据源名称)`

#### 6. `get_end_of_day_data(code)`
- **功能**：获取尾盘数据
- **参数**：
  - `code`：股票代码
- **返回**：`(尾盘数据字典, 数据源名称)`

#### 7. `get_data_with_fallback(data_type, **kwargs)`
- **功能**：通用数据获取方法，带自动切换数据源
- **参数**：
  - `data_type`：数据类型（sector_rankings, all_stocks, stock_daily, realtime, end_of_day）
  - `**kwargs`：其他参数
- **返回**：`(数据, 数据源名称)`

## 3. 切换规则

### 自动切换逻辑
1. **OpenBB**：作为主数据源，优先使用
2. **Akshare**：OpenBB失败时使用
3. **Efinance**：Akshare失败时使用
4. **Eastmoney**：Efinance失败时使用
5. **本地缓存**：所有数据源失败时使用

### 异常处理
- **超时处理**：OpenBB请求设置20秒超时
- **重试机制**：失败后自动分梯度重试（3秒→8秒→15秒），共3次
- **数据校验**：获取数据后自动校验字段完整性和合理性

## 4. 异常处理流程

1. **数据源异常**：
   - 记录详细错误信息到日志
   - 自动切换到下一个数据源
   - 推送告警到豆包

2. **数据异常**：
   - 校验数据完整性（核心字段不能为空）
   - 校验数据合理性（如A股涨幅≤10%、成交量≥0等）
   - 异常值自动标记并替换为备用源数据

3. **全源失效**：
   - 自动调用本地缓存的最新有效数据
   - 保证程序不中断
   - 推送严重告警到豆包

## 5. 本地缓存机制

- **缓存存储**：使用SQLite数据库，按股票代码+日期分区
- **缓存策略**：
  - 板块数据：缓存2小时
  - 股票数据：缓存2小时
  - 历史数据：缓存24小时
- **缓存读取**：所有数据源失败时，自动读取缓存数据

## 6. 测试验证

### 测试脚本
- `scripts/test_openbb_integration.py`：测试OpenBB数据源集成情况

### 测试场景
1. **正常场景**：验证OpenBB主源数据获取正常
2. **主源失效**：模拟OpenBB超时，验证自动切换到Akshare
3. **全源失效**：验证调用本地缓存数据

### 执行测试
```bash
python scripts/test_openbb_integration.py
```

## 7. 数据源优先级

最终数据源优先级：
**OpenBB（主）→ Akshare（备1）→ Efinance（备2）→ Eastmoney（备3）→ 本地缓存（兜底）**

## 8. 注意事项

1. **OpenBB安装**：如果安装失败，系统会自动降级使用备用数据源
2. **网络环境**：确保网络连接稳定，避免频繁切换数据源
3. **缓存管理**：定期清理过期缓存，保持缓存数据的有效性
4. **日志监控**：关注数据源切换日志，及时发现潜在问题

## 9. 后续优化

1. **OpenBB API适配**：根据OpenBB的实际API，完善数据获取逻辑
2. **性能优化**：优化数据获取和缓存机制，提高系统响应速度
3. **监控增强**：增加更详细的数据源监控和告警机制
4. **扩展数据源**：根据需要添加其他数据源作为补充
