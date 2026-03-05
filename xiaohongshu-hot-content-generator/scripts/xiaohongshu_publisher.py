#!/usr/bin/env python3
import subprocess
import json
import os
import requests
from config import OUTPUT_DIR, XIAOHONGSHU_COOKIES


def parse_cookies(cookie_string):
    cookies = {}
    if not cookie_string:
        return cookies
    for item in cookie_string.split(';'):
        item = item.strip()
        if '=' in item:
            key, value = item.split('=', 1)
            cookies[key.strip()] = value.strip()
    return cookies


def check_cookies():
    if not XIAOHONGSHU_COOKIES:
        return False, "XIAOHONGSHU_COOKIES 未在 .env 文件中配置"
    cookies = parse_cookies(XIAOHONGSHU_COOKIES)
    if not cookies.get('web_session'):
        return False, "cookies 中缺少 web_session"
    return True, "cookies 配置成功"


def download_image(url, local_path):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(local_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"❌ 下载图片失败: {str(e)}")
        return False


def publish_note(title, content, image_urls, tags=None):
    print("📕 准备发布小红书笔记...")

    ok, msg = check_cookies()
    if not ok:
        print(f"❌ {msg}")
        return False

    cookies = parse_cookies(XIAOHONGSHU_COOKIES)
    
    local_images = []
    try:
        for i, url in enumerate(image_urls):
            local_path = os.path.join(OUTPUT_DIR, f"temp_publish_{i}.png")
            if download_image(url, local_path):
                local_images.append(local_path)
        
        if not local_images:
            print("❌ 没有成功下载任何图片")
            return False

        ok, mcporter_path = check_mcporter()
        if not ok:
            print(f"❌ {mcporter_path}")
            return False

        ok, msg = check_xiaohongshu_mcp()
        if not ok:
            print(f"❌ {msg}")
            return False

        try:
            args = {
                "title": title,
                "content": content,
                "image_paths": local_images
            }
            if tags:
                args["tags"] = tags

            args_json = json.dumps(args, ensure_ascii=False)
            result = subprocess.run(
                [mcporter_path, "call", f'xiaohongshu.publish_note({args_json})'],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                print("✅ 小红书笔记发布成功！")
                print(f"输出: {result.stdout}")
                return True
            else:
                print(f"❌ 发布失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ 发布过程出错: {str(e)}")
            return False
        finally:
            for img_path in local_images:
                if os.path.exists(img_path):
                    os.remove(img_path)

    except Exception as e:
        print(f"❌ 发布过程出错: {str(e)}")
        return False


def check_mcporter():
    # 优先检查本地 node_modules 中的 mcporter
    local_mcporter = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "node_modules", ".bin", "mcporter")
    if os.path.exists(local_mcporter):
        return True, local_mcporter
        
    mcporter = subprocess.run(
        ["which", "mcporter"],
        capture_output=True,
        text=True
    )
    if mcporter.returncode != 0:
        return False, "mcporter 未安装，请先运行: npm install mcporter"
    return True, "mcporter"


def check_xiaohongshu_mcp():
    ok, mcporter_path = check_mcporter()
    if not ok:
        return False, mcporter_path
        
    try:
        result = subprocess.run(
            [mcporter_path, "config", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if "xiaohongshu" not in result.stdout:
            return False, "小红书 MCP 未配置，请参考 Agent-Reach 文档配置"
        return True, "小红书 MCP 已配置"
    except Exception as e:
        return False, f"检查小红书 MCP 失败: {str(e)}"


def check_login_status():
    ok, mcporter_path = check_mcporter()
    if not ok:
        return False, mcporter_path
        
    try:
        result = subprocess.run(
            [mcporter_path, "call", "xiaohongshu.check_login_status()"],
            capture_output=True,
            text=True,
            timeout=15
        )
        if "已登录" in result.stdout or "logged" in result.stdout.lower():
            return True, "已登录"
        return False, "未登录，请访问 http://localhost:18060 扫码登录"
    except Exception as e:
        return False, f"检查登录状态失败: {str(e)}"


def setup_guide():
    guide = """
========================================
  小红书发布功能配置指南
========================================

方式一：使用 .env 中的 cookies（推荐）
1. 在 .env 文件中配置 XIAOHONGSHU_COOKIES
2. 确保 cookies 包含 web_session、id_token、a1 等字段

方式二：使用 xiaohongshu-mcp + Docker
前置条件：
1. 安装 Docker
2. 安装 mcporter: npm install -g mcporter

配置步骤：
1. 启动 xiaohongshu-mcp 服务：
   docker run -d --name xiaohongshu-mcp -p 18060:18060 xpzouying/xiaohongshu-mcp

2. 注册到 mcporter：
   mcporter config add xiaohongshu http://localhost:18060/mcp

3. 扫码登录：
   访问 http://localhost:18060 ，用手机小红书 App 扫码登录

详细文档请参考: Agent-Reach/agent_reach/guides/setup-xiaohongshu.md
"""
    print(guide)

