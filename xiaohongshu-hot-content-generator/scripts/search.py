
import json
import subprocess
import os
from config import XIAOHONGSHU_SKILLS_PATH

def search_cases(topic=None):
    keyword = topic if topic else "OpenClaw 商业化 案例"
    print(f"🔍 正在通过 xiaohongshu-skills 搜索：{keyword}")
    
    try:
        # Run xiaohongshu-skills search-feeds
        result = subprocess.run(
            ["python3", "scripts/cli.py", "search-feeds", "--keyword", keyword, "--sort-by", "最多点赞"],
            cwd=XIAOHONGSHU_SKILLS_PATH,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"❌ 搜索失败: {result.stderr}")
            return None
            
        resp_json = json.loads(result.stdout)
        feeds = resp_json.get("feeds", [])
        
        # Filter out hot_query and empty titles
        valid_feeds = [f for f in feeds if f.get("modelType") == "note" and f.get("displayTitle")]
        
        if not valid_feeds:
            print("⚠️ 未找到相关笔记，使用默认主题")
            return {
                "title": keyword,
                "content": f"关于{keyword}的热门话题讨论",
                "source": "默认主题",
                "id": "default",
                "xsec_token": "default"
            }
            
        # Get details for the top note
        top_note = valid_feeds[0]
        print(f"✅ 选中案例: {top_note['displayTitle']}")
        
        # Get full detail for the selected note
        detail_result = subprocess.run(
            ["python3", "scripts/cli.py", "get-feed-detail", "--feed-id", top_note["id"], "--xsec-token", top_note["xsecToken"]],
            cwd=XIAOHONGSHU_SKILLS_PATH,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if detail_result.returncode == 0:
            detail_json = json.loads(detail_result.stdout)
            return {
                "title": detail_json.get("title") or top_note["displayTitle"],
                "content": detail_json.get("desc", ""),
                "source": "小红书",
                "id": top_note["id"],
                "xsec_token": top_note["xsecToken"]
            }
        else:
            print(f"⚠️ 获取详情失败，使用基本信息: {detail_result.stderr}")
            return {
                "title": top_note["displayTitle"],
                "content": "",
                "source": "小红书",
                "id": top_note["id"],
                "xsec_token": top_note["xsecToken"]
            }
            
    except Exception as e:
        print(f"❌ 搜索过程出错: {str(e)}")
        return None

def web_search(query: str, count: int = 5) -> list:
    # Keep this for compatibility if needed, but redirects to search_cases
    case = search_cases(query)
    return [case] if case else []
