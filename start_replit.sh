#!/bin/bash

# Replit 启动脚本

echo "==================================="
echo "启动 A股量化分析系统"
echo "==================================="

# 设置时区
export TZ='Asia/Shanghai'

# 检查 Python 版本
python --version

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "创建虚拟环境..."
    python -m venv .venv
fi

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
echo "检查并安装依赖..."
pip install --quiet --upgrade pip
pip install --quiet --prefer-binary -r requirements.txt

# 检查环境变量文件
if [ ! -f ".env" ]; then
    echo "创建 .env 文件..."
    cp .env.example .env
    echo "请编辑 .env 文件并填入必要的配置"
    echo "特别是 DOUBAO_API_KEY"
fi

# 创建必要的目录
mkdir -p data
mkdir -p logs
mkdir -p data/backup
mkdir -p data/cache

# 初始化数据库
echo "初始化数据库..."
python -c "from src.data.data_manager import get_data_manager; dm = get_data_manager(); print('Database initialized')"

# 启动主程序
echo "==================================="
echo "启动主程序..."
echo "==================================="
python main.py