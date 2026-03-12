
import json
import subprocess
import os
import requests
from config import XIAOHONGSHU_SKILLS_PATH, OUTPUT_DIR, XIAOHONGSHU_COOKIES

def check_login_status():
    """使用 xiaohongshu-skills 检查登录状态。"""
    try:
        # 确保 cookies 已注入
        inject_cookies()
        
        result = subprocess.run(
            ["python3", "scripts/cli.py", "check-login"],
            cwd=XIAOHONGSHU_SKILLS_PATH,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            resp = json.loads(result.stdout)
            if resp.get("logged_in"):
                return True, "已登录"
        return False, "未登录，请检查 cookies 或运行 login"
    except Exception as e:
        return False, f"检查登录状态失败: {str(e)}"

def inject_cookies():
    """注入 XIAOHONGSHU_COOKIES 到正在运行的 Chrome。"""
    if not XIAOHONGSHU_COOKIES:
        return False
    try:
        subprocess.run(
            ["python3", "scripts/set_cookies.py", "--cookies", XIAOHONGSHU_COOKIES],
            cwd=XIAOHONGSHU_SKILLS_PATH,
            capture_output=True,
            text=True,
            timeout=30
        )
        return True
    except Exception:
        return False

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
    print("📕 准备发布小红书笔记 (使用 xiaohongshu-skills)...")
    
    # 1. 检查并注入 cookies
    ok, msg = check_login_status()
    if not ok:
        print(f"❌ {msg}")
        return False

    # 2. 下载图片到临时文件
    local_images = []
    title_file = os.path.join(OUTPUT_DIR, "temp_title.txt")
    content_file = os.path.join(OUTPUT_DIR, "temp_content.txt")
    
    try:
        for i, url in enumerate(image_urls):
            local_path = os.path.join(OUTPUT_DIR, f"temp_publish_{i}.png")
            if download_image(url, local_path):
                local_images.append(local_path)
        
        if not local_images:
            print("❌ 没有成功下载任何图片")
            return False

        # 3. 准备标题和内容文件
        with open(title_file, "w", encoding="utf-8") as f:
            f.write(title)
        with open(content_file, "w", encoding="utf-8") as f:
            f.write(content)

        # 4. 调用 xiaohongshu-skills publish
        cmd = ["python3", "scripts/cli.py", "publish", 
               "--title-file", title_file, 
               "--content-file", content_file,
               "--images"] + local_images
        
        if tags:
            cmd.extend(["--tags"] + tags)

        print(f"🚀 执行发布命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=XIAOHONGSHU_SKILLS_PATH,
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
            # 如果是因为未登录，尝试重新注入
            if "未登录" in result.stderr:
                print("🔄 尝试重新注入 cookies...")
                inject_cookies()
            return False

    except Exception as e:
        print(f"❌ 发布过程出错: {str(e)}")
        return False
    finally:
        # 清理临时文件
        for img_path in local_images:
            if os.path.exists(img_path):
                os.remove(img_path)
        if os.path.exists(title_file):
            os.remove(title_file)
        if os.path.exists(content_file):
                os.remove(content_file)
