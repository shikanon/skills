#!/bin/bash

set -e

echo "========================================="
echo "  小红书热门内容生成器 - 安装脚本"
echo "========================================="

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_NAME="xiaohongshu-hot-content-generator-venv"
PYTHON_VERSION="3.11"

cd "$PROJECT_DIR"

echo ""
echo "📁 项目目录: $PROJECT_DIR"
echo ""

update_submodule() {
    echo "🔧 更新子模块..."
    git submodule update --init --recursive
    echo "✅ 子模块更新成功"
}

check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "❌ 未找到 Python，请先安装 Python 3.11 或更高版本"
        exit 1
    fi

    PYTHON_VERSION_DETECTED=$($PYTHON_CMD --version | awk '{print $2}')
    echo "✅ 检测到 Python 版本: $PYTHON_VERSION_DETECTED"
}

create_venv() {
    echo ""
    echo "🔧 创建虚拟环境..."
    
    if [ -d "$VENV_NAME" ]; then
        echo "⚠️  虚拟环境已存在，跳过创建"
    else
        $PYTHON_CMD -m venv "$VENV_NAME"
        echo "✅ 虚拟环境创建成功"
    fi
}

activate_venv() {
    echo ""
    echo "🔧 激活虚拟环境..."
    
    if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
        source "$VENV_NAME/bin/activate"
    else
        source "$VENV_NAME/Scripts/activate"
    fi
    
    echo "✅ 虚拟环境已激活"
}

install_dependencies() {
    echo ""
    echo "📦 安装依赖..."
    
    pip install --upgrade pip
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        echo "✅ 依赖安装完成"
    else
        echo "⚠️  未找到 requirements.txt"
    fi
}

create_env_example() {
    echo ""
    echo "📝 配置环境变量..."
    
    if [ -f ".env" ]; then
        echo "✅ .env 文件已存在"
        return
    fi
    
    echo ""
    echo "请提供以下 API 密钥（可先设置环境变量，或在此处输入）："
    echo ""
    
    # 尝试从环境变量读取，如果没有则交互式输入
    if [ -n "$ARK_API_KEY" ]; then
        echo "✅ 使用环境变量 ARK_API_KEY"
        ARK_KEY="$ARK_API_KEY"
    else
        read -p "请输入 ARK_API_KEY: " ARK_KEY
    fi
    
    if [ -n "$TOS_ACCESS_KEY" ]; then
        echo "✅ 使用环境变量 TOS_ACCESS_KEY"
        TOS_ACCESS="$TOS_ACCESS_KEY"
    else
        read -p "请输入 TOS_ACCESS_KEY: " TOS_ACCESS
    fi
    
    if [ -n "$TOS_SECRET_KEY" ]; then
        echo "✅ 使用环境变量 TOS_SECRET_KEY"
        TOS_SECRET="$TOS_SECRET_KEY"
    else
        read -p "请输入 TOS_SECRET_KEY: " TOS_SECRET
    fi
    
    # 检查是否所有密钥都已提供
    if [ -z "$ARK_KEY" ] || [ -z "$TOS_ACCESS" ] || [ -z "$TOS_SECRET" ]; then
        echo ""
        echo "❌ 错误：缺少必要的 API 密钥！"
        echo ""
        echo "请提供以下密钥："
        echo "  - ARK_API_KEY: 用于调用大模型 API"
        echo "  - TOS_ACCESS_KEY: 对象存储访问密钥"
        echo "  - TOS_SECRET_KEY: 对象存储密钥"
        echo ""
        echo "获取方式："
        echo "  1. 火山引擎 ARK: https://console.volcengine.com/ark"
        echo "  2. 火山引擎 TOS: https://console.volcengine.com/tos"
        echo ""
        echo "你可以通过以下方式提供密钥："
        echo "  - 在运行 install.sh 前设置环境变量"
        echo "  - 或者在交互式提示时输入"
        echo ""
        exit 1
    fi
    
    # 创建 .env 文件
    cat > .env << EOF
ARK_API_KEY=$ARK_KEY
TOS_ACCESS_KEY=$TOS_ACCESS
TOS_SECRET_KEY=$TOS_SECRET
EOF
    echo "✅ .env 文件创建成功"
}

show_finish_info() {
    echo ""
    echo "========================================="
    echo "  🎉 安装完成！"
    echo "========================================="
    echo ""
    echo "使用说明："
    echo "1. 激活虚拟环境: source $VENV_NAME/bin/activate"
    echo "2. 运行脚本: python scripts/generate_content.py"
    echo ""
    echo "如需更新项目，请运行: ./update.sh"
    echo ""
}

check_python
update_submodule
create_venv
activate_venv
install_dependencies
create_env_example
show_finish_info

