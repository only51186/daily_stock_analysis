# Replit 上传完整清单

## 📋 上传前检查清单

### ✅ 必须上传的文件和目录

#### 1. 核心配置文件（必须）
```
✅ requirements.txt              # Python依赖包列表
✅ .env.example                 # 环境变量示例文件
✅ .replit                     # Replit项目配置
✅ replit.nix                  # Replit Nix包配置
✅ start_replit.sh             # Replit启动脚本
✅ .gitignore                  # Git忽略文件配置
```

#### 2. 主程序文件（必须）
```
✅ main.py                     # 主程序入口
✅ webui.py                    # Web UI界面
✅ server.py                   # 服务器程序
✅ analyzer_service.py          # 分析服务
```

#### 3. 数据下载和验证程序（必须）
```
✅ comprehensive_data_download.py    # 综合数据下载程序
✅ smart_data_validator.py          # 智能数据验证器
✅ adaptive_stock_selector.py       # 自适应选股程序
✅ check_real_data_date.py         # 检查真实数据日期
✅ query_stock_total.py            # 查询股票总数
✅ check_stock_count.py            # 检查股票数量
✅ check_data_date.py              # 检查数据日期
```

#### 4. src/ 目录（必须，包含所有核心模块）
```
✅ src/__init__.py
✅ src/agent/                      # AI代理模块
✅ src/backtest_layer/             # 回测模块
✅ src/core/                       # 核心功能模块
✅ src/data_layer/                 # 数据层模块
✅ src/factor_layer/               # 因子模块
✅ src/market_analysis/             # 市场分析模块
✅ src/notification/                # 通知模块
✅ src/notification_sender/         # 通知发送模块
✅ src/openbb_data/                # OpenBB数据模块
✅ src/repositories/               # 数据仓库模块
✅ src/scheduler/                  # 调度器模块
   ✅ src/scheduler/auto_scheduler.py
   ✅ src/scheduler/smart_auto_scheduler.py
✅ src/services/                   # 服务模块
✅ src/strategies/                 # 策略模块
✅ src/*.py                        # 其他核心文件
```

#### 5. scripts/ 目录（必须，包含所有脚本）
```
✅ scripts/__init__.py
✅ scripts/smart_evening_stock_selector.py
✅ scripts/auto_data_downloader.py
✅ scripts/evening_stock_selector.py
✅ scripts/evening_stock_selector_v2.py
✅ scripts/evening_stock_selector_v3.py
✅ scripts/market_review.py
✅ scripts/strategy_backtest.py
✅ scripts/strategy_backtest_optimized.py
✅ scripts/short_term_selector.py
✅ scripts/end_of_day_selector.py
✅ scripts/hs_mainboard_short_strategy.py
✅ scripts/hs_mainboard_close_strategy.py
✅ scripts/master_strategy_backtester.py
✅ scripts/strategy_optimizer.py
✅ scripts/daily_review.py
✅ scripts/closing_stock_selector.py
✅ scripts/unified_scheduler.py
✅ scripts/stock_prediction_ui.py
✅ scripts/yibin_analysis.py
✅ scripts/trae_stock_analyze.py
✅ scripts/check_db.py
✅ scripts/check_packages.py
✅ scripts/test_*.py                 # 所有测试文件
```

#### 6. api/ 目录（必须，Web API）
```
✅ api/__init__.py
✅ api/app.py
✅ api/deps.py
✅ api/middlewares/                 # 中间件
✅ api/v1/                          # API v1
   ✅ api/v1/__init__.py
   ✅ api/v1/router.py
   ✅ api/v1/endpoints/             # API端点
   ✅ api/v1/schemas/               # 数据模型
```

#### 7. apps/ 目录（可选，前端应用）
```
✅ apps/dsa-desktop/                # 桌面应用
✅ apps/dsa-web/                    # Web应用
```

#### 8. utils/ 目录（必须，工具函数）
```
✅ utils/__init__.py
✅ utils/*.py                       # 所有工具函数
```

#### 9. 文档文件（推荐）
```
✅ README.md                        # 项目说明
✅ REPLIT_SETUP.md                  # Replit部署指南
✅ AUTO_RUN_GUIDE.md                # 自动运行指南
✅ QUICK_DEPLOY.md                  # 快速部署指南
✅ AGENTS.md                        # Agent配置说明
✅ 其他*.md文档                     # 其他文档
```

#### 10. 空目录（必须创建）
```
✅ data/                           # 数据目录（空）
✅ data/backup/                    # 备份目录（空）
✅ data/cache/                     # 缓存目录（空）
✅ logs/                           # 日志目录（空）
```

### ❌ 不需要上传的文件和目录

#### 1. 虚拟环境
```
❌ .venv/
❌ venv/
❌ ENV/
❌ env/
```

#### 2. Python缓存
```
❌ __pycache__/
❌ *.pyc
❌ *.pyo
❌ *.pyd
```

#### 3. 数据和日志
```
❌ data/*.db
❌ data/*.sqlite
❌ data/*.sqlite3
❌ logs/*.log
❌ *.log
❌ *.bak
❌ *.tmp
```

#### 4. 敏感配置
```
❌ .env
❌ .env.*
❌ config/secrets.py
❌ secrets.py
❌ *_secrets.py
```

#### 5. IDE配置
```
❌ .idea/
❌ .vscode/
❌ *.swp
❌ *.swo
❌ .cursorrules
```

#### 6. 系统文件
```
❌ .DS_Store
❌ Thumbs.db
```

#### 7. 测试和临时文件
```
❌ test_*.py                       # 根目录下的临时测试文件
❌ verify_*.py                     # 验证脚本
❌ backup/
❌ local/
```

#### 8. 构建产物
```
❌ build/
❌ dist/
❌ *.egg-info/
```

## 🚀 上传后使用步骤

### 步骤1：上传文件
将上述所有标记为 ✅ 的文件和目录上传到Replit

### 步骤2：配置环境变量
```bash
# 在Replit Shell中执行
cp .env.example .env

# 编辑.env文件，填入必要的配置
nano .env
```

**必须配置的变量：**
```env
DOUBAO_API_KEY=your_doubao_api_key_here
```

**可选配置的变量：**
```env
TUSHARE_TOKEN=your_tushare_token_here
DATA_SOURCE_PRIORITY=akshare,efinance,tushare
```

### 步骤3：安装依赖
```bash
# 方式1：使用启动脚本（推荐）
chmod +x start_replit.sh
./start_replit.sh

# 方式2：手动安装
pip install --prefer-binary -r requirements.txt
```

### 步骤4：创建必要目录
```bash
mkdir -p data
mkdir -p data/backup
mkdir -p data/cache
mkdir -p logs
```

### 步骤5：初始化数据库
```bash
python -c "from src.data.data_manager import get_data_manager; dm = get_data_manager(); print('Database initialized')"
```

### 步骤6：运行程序

#### 选项1：运行主程序
```bash
python main.py
```

#### 选项2：运行Web UI
```bash
python webui.py
```

#### 选项3：运行自动化调度器
```bash
python src/scheduler/smart_auto_scheduler.py
```

#### 选项4：下载股票数据
```bash
python comprehensive_data_download.py
```

#### 选项5：运行选股程序
```bash
python adaptive_stock_selector.py
```

## 📊 功能验证清单

上传后，按以下顺序验证功能：

### 1. 基础环境验证
```bash
# 检查Python版本
python --version

# 检查依赖安装
pip list

# 检查环境变量
cat .env
```

### 2. 数据库验证
```bash
# 初始化数据库
python -c "from src.data.data_manager import get_data_manager; dm = get_data_manager(); print('OK')"

# 检查数据库文件
ls -la data/
```

### 3. 数据下载验证
```bash
# 验证数据下载
python comprehensive_data_download.py
```

### 4. 数据验证
```bash
# 验证数据完整性
python smart_data_validator.py
```

### 5. 选股功能验证
```bash
# 运行选股程序
python adaptive_stock_selector.py
```

### 6. 自动化调度验证
```bash
# 运行自动化调度器
python src/scheduler/smart_auto_scheduler.py
```

## ⚠️ 常见问题解决

### 问题1：依赖安装失败
```bash
# 使用预编译包
pip install --prefer-binary -r requirements.txt

# 或者单独安装失败的包
pip install --prefer-binary package_name
```

### 问题2：数据库锁定
```bash
# 删除锁定文件
rm -f data/*.db-lock
```

### 问题3：内存不足
```bash
# 清理缓存
rm -rf data/cache/*
rm -rf __pycache__/
```

### 问题4：时区问题
```bash
# 检查时区设置
echo $TZ

# 设置时区
export TZ='Asia/Shanghai'
```

### 问题5：网络请求失败
```bash
# 增加超时时间
export REQUEST_TIMEOUT=60

# 使用代理（如果需要）
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port
```

## 📝 上传文件统计

### 必须上传的文件数量
- Python文件：约100+个
- 配置文件：约10个
- 文档文件：约20个
- 总计：约130+个文件

### 预估上传大小
- 源代码：约10-20MB
- 文档：约5-10MB
- 总计：约15-30MB

## ✅ 最终检查清单

上传前请确认：
- [ ] 所有 ✅ 标记的文件都已上传
- [ ] 所有 ❌ 标记的文件都已排除
- [ ] .env.example 文件已上传
- [ ] requirements.txt 文件已上传
- [ ] .replit 文件已上传
- [ ] replit.nix 文件已上传
- [ ] start_replit.sh 文件已上传
- [ ] src/ 目录完整上传
- [ ] scripts/ 目录完整上传
- [ ] data/ 目录已创建（空）
- [ ] logs/ 目录已创建（空）

## 🎉 上传完成

上传完成后，按照上述步骤配置和运行，系统应该可以正常工作！

如有问题，请参考 REPLIT_SETUP.md 文档。