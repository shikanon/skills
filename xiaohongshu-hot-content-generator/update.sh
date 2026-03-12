#!/bin/bash

set -e

echo "========================================="
echo "  小红书热门内容生成器 - 更新脚本"
echo "========================================="

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_NAME="xiaohongshu-hot-content-generator-venv"

cd "$PROJECT_DIR"

echo ""
echo "📁 项目目录: $PROJECT_DIR"
echo ""

check_git() {
    if command -v git &> /dev/null; then
        echo "✅ Git 已安装"
        return 0
    else
        echo "⚠️  未检测到 Git，跳过代码拉取"
        return 1
    fi
}

pull_latest_code() {
    if [ -d ".git" ]; then
        echo ""
        echo "🔄 拉取最新代码..."
        
        if git status --porcelain | grep -q .; then
            echo "⚠️  检测到本地修改，请先提交或暂存更改"
            git status
            read -p "是否继续更新？(y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "❌ 更新已取消"
                exit 1
            fi
        fi
        
        git pull
        echo "🔄 更新子模块..."
        git submodule update --init --recursive
        echo "✅ 子模块已更新"
        echo "✅ 代码已更新到最新版本"
    else
        echo "⚠️  非 Git 仓库，跳过代码拉取"
    fi
}

activate_venv() {
    echo ""
    echo "🔧 激活虚拟环境..."
    
    if [ ! -d "$VENV_NAME" ]; then
        echo "❌ 虚拟环境不存在，请先运行 ./install.sh"
        exit 1
    fi
    
    if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
        source "$VENV_NAME/bin/activate"
    else
        source "$VENV_NAME/Scripts/activate"
    fi
    
    echo "✅ 虚拟环境已激活"
}

update_dependencies() {
    echo ""
    echo "📦 更新依赖..."
    
    pip install --upgrade pip
    
    if [ -f "requirements.txt" ]; then
        pip install --upgrade -r requirements.txt
        echo "✅ 依赖已更新"
    else
        echo "⚠️  未找到 requirements.txt"
    fi
}

check_env_file() {
    echo ""
    echo "📝 检查环境配置..."
    
    if [ ! -f ".env" ]; then
        echo "⚠️  未找到 .env 文件"
        if [ -f ".env.example" ]; then
            cp .env.example .env
            echo "✅ 已从 .env.example 创建 .env 文件，请编辑并填入 API 密钥"
        fi
    else
        echo "✅ .env 文件存在"
    fi
}

show_finish_info() {
    echo ""
    echo "========================================="
    echo "  🎉 更新完成！"
    echo "========================================="
    echo ""
    echo "下一步操作："
    echo "1. 激活虚拟环境: source $VENV_NAME/bin/activate"
    echo "2. 运行脚本: python scripts/generate_content.py"
    echo ""
}

check_git && pull_latest_code
activate_venv
update_dependencies
check_env_file
show_finish_info

