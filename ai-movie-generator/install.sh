#!/bin/bash

echo "🚀 开始安装 AI Movie Generator 依赖..."

# Check if python3 is installed
if ! command -v python3 &> /dev/null
then
    echo "❌ 错误: 未找到 python3，请先安装。"
    exit 1
fi

# Create virtual environment if needed
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "📥 安装 Python 依赖包..."
pip install -r requirements.txt

# Create necessary directories
mkdir -p data output references scripts

echo "✅ 安装完成！"
echo "请在 .env 文件中配置 ARK_API_KEY 后，运行: python3 -m scripts.generate_content --script '你的剧本'"
