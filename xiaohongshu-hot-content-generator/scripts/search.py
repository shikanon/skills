#!/usr/bin/env python3
import json
import requests
from config import ARK_API_KEY, ARK_BASE_URL, WEB_SEARCH_MODEL

def web_search(query: str, count: int = 5) -> list:
    print(f"🔍 正在搜索：{query}")
    url = f"{ARK_BASE_URL}/responses"
    headers = {
        "Authorization": f"Bearer {ARK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": WEB_SEARCH_MODEL,
        "stream": False,
        "tools": [
            {
                "type": "web_search",
                "max_keyword": 4,
                "sources": ["douyin", "moji", "toutiao"],
            }
        ],
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"请搜索最新热点，按热度和相关性排序：{query}"
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            print(f"❌ 接口返回错误: {response.status_code} - {response.text}")
            return []
            
        resp_json = response.json()
        
        content = ""
        if "choices" in resp_json and len(resp_json["choices"]) > 0:
            choice = resp_json["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                msg_content = choice["message"]["content"]
                if isinstance(msg_content, list):
                    for item in msg_content:
                        if isinstance(item, dict):
                            content += item.get("text", "")
                            if not item.get("text") and "content" in item:
                                content += str(item["content"])
                        elif isinstance(item, str):
                            content += item
                else:
                    content = str(msg_content)
        
        if not content and "output" in resp_json:
            content = str(resp_json["output"])
        
        if content:
            print(f"✅ 搜索完成，获取到内容长度：{len(content)}")
            return [{
                "title": f"{query} 相关案例",
                "content": content,
                "source": "联网搜索"
            }]
        
        print(f"⚠️ 搜索未返回内容。完整响应：{json.dumps(resp_json, ensure_ascii=False)}")
        return []
    except Exception as e:
        print(f"❌ 搜索失败: {str(e)}")
        return []

def search_cases(topic=None):
    if topic:
        print(f"🔍 正在搜索{topic}相关案例...")
        cases = web_search(f"{topic} 相关案例", count=5)
    else:
        print("🔍 正在搜索OpenClaw商业化变现相关案例...")
        cases = web_search("OpenClaw 商业化 案例", count=5)
    
    if not cases:
        raise Exception("❌ 搜索未返回内容且已移除兜底策略")
    
    selected_case = cases[0]
    print(f"✅ 选中案例: {selected_case['title']}")
    return selected_case

