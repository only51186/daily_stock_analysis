# GitHub 快速部署指南

## 5 分钟快速部署

### 第一步：准备 API 密钥

1. 获取豆包 API 密钥：https://console.volcengine.com/ark
2. （可选）获取 Tushare Token：https://tushare.pro/register

### 第二步：创建 GitHub 仓库

1. 在 GitHub 创建新仓库
2. 将本地代码推送到 GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/your-username/your-repo.git
git push -u origin main
```

### 第三步：配置 GitHub Secrets

1. 进入仓库的 Settings → Secrets and variables → Actions
2. 添加以下 Secrets：

| Secret 名称 | 说明 |
|-----------|------|
| `DOUBAO_API_KEY` | 你的豆包 API 密钥 |
| `TUSHARE_TOKEN` | 你的 Tushare Token（可选） |

### 第四步：验证部署

运行验证脚本：

```bash
python verify_deployment.py
```

### 第五步：测试功能

#### 测试选股

```bash
python scripts/end_of_day_selector.py
```

#### 测试回测

```bash
python scripts/strategy_backtest.py
```

#### 测试推送

```bash
python -c "from utils.notification_sender import get_notification_sender; sender = get_notification_sender(); sender.send_custom_message('测试', '部署成功！')"
```

## 使用 GitHub Codespaces

1. 在 GitHub 仓库页面点击 "Code" → "Codespaces" → "Create codespace on main"
2. 等待 Codespaces 启动
3. 在终端中运行：

```bash
# 配置环境变量
echo "DOUBAO_API_KEY=your_doubao_api_key_here" >> .env

# 运行项目
python main.py
```

## 使用 GitHub Actions

项目已配置自动运行的工作流：

- **每日选股**: 每天 14:30（北京时间）自动运行
- **每周回测**: 每周日 20:00（北京时间）自动运行
- **手动触发**: 在 Actions 页面手动触发

查看结果：
1. 进入仓库的 Actions 页面
2. 选择对应的工作流
3. 查看运行日志和下载结果

## 常见问题

### Q: 如何查看 API 密钥是否配置正确？

A: 运行以下命令：

```bash
python -c "from config.settings import get_settings; settings = get_settings(); print(f'API Key: {settings.doubao.api_key[:10]}...')"
```

### Q: 如何修改定时任务时间？

A: 编辑 `.env` 文件中的以下配置：

```env
SCHEDULE_DATA_DOWNLOAD_TIMES=09:30,14:00
SCHEDULE_SELECTION_TIME=14:30
SCHEDULE_BACKTEST_TIME=20:00
```

### Q: 如何在 GitHub Actions 中查看日志？

A: 进入 Actions 页面，点击对应的工作流运行记录，查看详细日志。

### Q: 如何下载 GitHub Actions 生成的结果？

A: 在 Actions 页面的工作流运行记录中，点击 "Artifacts" 部分下载结果文件。

## 下一步

- 查看 [GITHUB_DEPLOYMENT.md](GITHUB_DEPLOYMENT.md) 了解详细部署指南
- 查看 [GITHUB_ADAPTATION_REPORT.md](GITHUB_ADAPTATION_REPORT.md) 了解适配详情
- 查看 [README.md](README.md) 了解项目功能

## 获取帮助

如有问题，请：

1. 查看 [FAQ.md](docs/FAQ.md)
2. 提交 [Issue](https://github.com/your-repo/issues)
3. 查看 [完整指南](docs/full-guide.md)
