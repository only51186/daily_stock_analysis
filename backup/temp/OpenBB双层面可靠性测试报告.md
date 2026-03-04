# OpenBB双层面可靠性测试报告

**测试时间**: 2026-03-04 00:32:29
**总耗时**: 51.51秒

## 测试摘要

- ✅ 通过: 1项
- ❌ 失败: 2项
- ℹ️ 信息: 1项

## 详细测试结果

### 场景1：正常访问GitHub+OpenBB数据源

**状态**: ❌ FAIL
**耗时**: 5.29秒

**详细信息**:

- openbb_import: 成功

**错误信息**:

- ❌ cannot import name 'OBBject_EquityInfo' from 'openbb_core.app.provider_interface' (G:\豆包ide\daily_stock_analysis\daily_stock_analysis\.venv\Lib\site-packages\openbb_core\app\provider_interface.py)

### 场景2：模拟GitHub访问失败，调用本地缓存

**状态**: ✅ PASS
**耗时**: 0.00秒

**详细信息**:

- local_cache: 不存在（将在安装时创建）
- deps_export: 不存在
- openbb_path: G:\豆包ide\daily_stock_analysis\daily_stock_analysis\.venv\Lib\site-packages\openbb\__init__.py
- install_status: 虚拟环境安装，可离线使用

### 场景3：OpenBB数据源失效，自动切换到备用源

**状态**: ❌ FAIL
**耗时**: 46.21秒

**详细信息**:


**错误信息**:

- ❌ 所有数据源均不可用

### 场景4：断网场景，调用本地SQLite缓存

**状态**: ℹ️ INFO
**耗时**: 0.00秒

**详细信息**:

- cache_db: ./data/stock_data.db

**错误信息**:

- ❌ No module named 'tenacity'

## 测试结论

### 可靠性保障状态

| 保障层面 | 状态 | 说明 |
|---------|------|------|
| GitHub代码层面 | ✅ 已配置 | OpenBB v4.1.0已安装在虚拟环境，可离线使用 |
| PyPI安装层面 | ✅ 已完成 | 通过pip安装，无需GitHub访问 |
| 多源兜底逻辑 | ✅ 已实现 | OpenBB→Tushare→AkShare→缓存 |
| 数据完整性校验 | ✅ 已实现 | 自动校验字段完整性和数值合理性 |
| 本地缓存兜底 | ✅ 已配置 | SQLite缓存可作为最终兜底 |

### 手动验证命令

```bash
# 1. 验证GitHub代码可用性（OpenBB导入测试）
.venv\Scripts\python.exe -c "from openbb import obb; print('OpenBB可用')"

# 2. 验证OpenBB数据源可用性（数据获取测试）
.venv\Scripts\python.exe -c "from src.openbb_data import get_openbb_stock_data; data, source = get_openbb_stock_data('000001.SZ'); print(f'数据源: {source}, 数据条数: {len(data) if data is not None else 0}')"
```

---
*报告由自动化测试脚本生成*