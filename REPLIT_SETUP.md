# Replit 部署指南

## 项目简介

这是一个A股量化分析系统，支持数据下载、选股、回测、因子计算等功能。

## Replit 环境要求

- Python 3.11+
- 至少 2GB RAM
- 推荐使用 4GB+ RAM

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入必要的配置：

```env
# 必填配置
DOUBAO_API_KEY=your_doubao_api_key_here

# 可选配置
DATA_SOURCE_PRIORITY=akshare,efinance,tushare
TUSHARE_TOKEN=your_tushare_token_here
```

### 3. 初始化数据库

```bash
python -c "from src.data.data_manager import get_data_manager; dm = get_data_manager(); print('Database initialized')"
```

### 4. 运行程序

#### 方式1：运行主程序
```bash
python main.py
```

#### 方式2：运行Web UI
```bash
python webui.py
```

#### 方式3：运行自动化调度器
```bash
python src/scheduler/smart_auto_scheduler.py
```

#### 方式4：运行数据下载
```bash
python comprehensive_data_download.py
```

#### 方式5：运行选股程序
```bash
python adaptive_stock_selector.py
```

## Replit 特殊配置

### 1. 时区设置

项目已配置为使用 `Asia/Shanghai` 时区，确保时间计算正确。

### 2. 数据持久化

Replit 的文件系统是持久的，但建议定期备份数据：

```bash
# 备份数据库
cp data/stock_analysis.db data/stock_analysis_backup_$(date +%Y%m%d).db
```

### 3. 资源限制

Replit 免费版有资源限制：
- CPU: 0.5-1 vCPU
- RAM: 512MB - 1GB
- 网络请求: 有限制

建议升级到付费版以获得更好的性能。

### 4. 网络请求

Replit 的网络请求可能较慢，建议：
- 增加请求超时时间
- 使用缓存机制
- 减少并发请求数量

## 常见问题

### 1. 依赖安装失败

某些依赖可能需要编译，建议：

```bash
# 使用预编译包
pip install --prefer-binary -r requirements.txt
```

### 2. 数据库锁定

SQLite 在并发访问时可能锁定，建议：

```env
# 在 .env 中设置
DATABASE_TIMEOUT=30
```

### 3. 内存不足

如果遇到内存不足问题：

```bash
# 清理缓存
rm -rf data/cache/*
rm -rf __pycache__/
```

### 4. 时区问题

确保时区设置正确：

```python
import os
os.environ['TZ'] = 'Asia/Shanghai'
```

## 性能优化建议

### 1. 使用缓存

```env
# 在 .env 中启用缓存
DATA_CACHE_ENABLED=true
DATA_CACHE_TTL_HOURS=24
```

### 2. 减少数据量

```env
# 只下载主板股票
DATA_SOURCE_FILTER=main_board
```

### 3. 调整任务频率

```env
# 减少定时任务频率
SCHEDULE_DATA_DOWNLOAD_TIMES=09:30
```

## 监控和日志

### 查看日志

```bash
# 查看最新日志
tail -f logs/auto_scheduler.log

# 查看错误日志
tail -f logs/error.log
```

### 监控资源使用

```bash
# 查看内存使用
free -h

# 查看磁盘使用
df -h
```

## 更新和维护

### 更新依赖

```bash
pip install --upgrade -r requirements.txt
```

### 备份数据

```bash
# 备份整个项目
tar -czf backup_$(date +%Y%m%d).tar.gz data/ logs/
```

## 技术支持

如有问题，请查看：
- 项目 README.md
- 项目文档 docs/
- GitHub Issues

## 注意事项

1. **API 密钥安全**：不要将 `.env` 文件提交到公开仓库
2. **数据备份**：定期备份重要数据
3. **资源监控**：注意 Replit 的资源使用情况
4. **网络限制**：注意 API 调用频率限制
5. **时区设置**：确保时区配置正确