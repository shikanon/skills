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
    
    if [ ! -f ".env" ]; then
        cat > .env.example << 'EOF'
ARK_API_KEY=your_ark_api_key
TOS_ACCESS_KEY=your_tos_access_key
TOS_SECRET_KEY=your_tos_secret_key
EOF
        echo "✅ 创建 .env.example 文件"
        
        if [ ! -f ".env" ]; then
            cp .env.example .env
            echo "⚠️  请编辑 .env 文件，填入真实的 API 密钥"
        fi
    else
        echo "✅ .env 文件已存在"
    fi
}

show_finish_info() {
    echo ""
    echo "========================================="
    echo "  🎉 安装完成！"
    echo "========================================="
    echo ""
    echo "使用说明："
    echo "1. 编辑 .env 文件，填入 API 密钥"
    echo "2. 激活虚拟环境: source $VENV_NAME/bin/activate"
    echo "3. 运行脚本: python scripts/generate_content.py"
    echo ""
    echo "如需更新项目，请运行: ./update.sh"
    echo ""
}

check_python
create_venv
activate_venv
install_dependencies
create_env_example
show_finish_info

