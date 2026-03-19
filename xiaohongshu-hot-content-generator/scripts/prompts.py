#!/usr/bin/env python3
import json
import os
from datetime import datetime
from config import client, OUTPUT_DIR, LLM_MODEL
from uploader import upload_to_tos

def _call_llm(system_prompt, user_prompt):
    """通用LLM调用函数"""
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()
    except Exception as e:
        print(f"❌ LLM调用失败: {str(e)}")
        raise

def generate_prompts(case):
    print("✍️ 正在开始多阶段图文内容生成...")
    
    # 第一步：策划热点和有吸引力的方向
    print("1️⃣ 正在策划内容方向...")
    planning_system_prompt = """
    你是小红书资深运营专家，擅长洞察流量密码。
    请基于用户提供的主题/案例，策划3个极具爆款潜力的内容创作方向。
    要求：
    1. 每个方向需包含：核心痛点、情绪价值点、目标受众、预期的点击理由。
    2. 方向需具有差异化（如：避雷指南、新手保姆级、行业内幕揭秘、情绪共鸣等）。
    3. 严格返回JSON格式：{"directions": [{"title": "方向名", "reason": "为什么会火", "strategy": "创作策略"}]}
    """
    planning_user_prompt = f"主题：{case.get('title', '')}\n内容概要：{case.get('content', '')}"
    plan_json_str = _call_llm(planning_system_prompt, planning_user_prompt)
    plan_data = json.loads(plan_json_str)
    # 选取第一个方向作为执行方向（或可扩展为由LLM自动选择最优方向）
    best_direction = plan_data['directions'][0]
    print(f"✅ 确定创作方向: {best_direction['title']}")

    # 第二步：生成标题、文案和标签
    print("2️⃣ 正在生成标题、文案和标签...")
    content_system_prompt = """
    你是小红书爆款文案师。请基于选定的策划方向生成文案。
    要求：
    1. 标题（title）：15字内，带情绪感/干货感/热点感，带1-2个emoji。
    2. 文案（copy）：口语化，多用emoji，开头吸睛，中间分点（短句为主），结尾引导互动。
    3. 标签（tags）：数组，6-10个相关热门标签。
    严格返回JSON格式：{"title": "...", "copy": "...", "tags": [...]}
    """
    content_user_prompt = f"策划方向：{best_direction['title']} ({best_direction['strategy']})\n原始案例内容：{case.get('content', '')}"
    content_json_str = _call_llm(content_system_prompt, content_user_prompt)
    content_data = json.loads(content_json_str)
    print(f"✅ 文案生成完成: {content_data['title']}")

    # 第三步：基于文案生成图片提示词
    print("3️⃣ 正在生成图片提示词...")
    image_system_prompt = """
    你是视觉设计师，擅长将文字转化为高点击率的视觉画面。
    请基于文案内容生成3张图片的描述（prompt）。
    
    ⚠️ 强制性约束：
    1. 图片prompt中绝对不能出现“小红书”字样、Logo或任何提及“小红书”的内容（如"小红书博主"、"小红书风格"等词汇）。
    2. 提示词应包含：场景、主体、构图、光影、设计元素。
    3. 第一张为封面：视觉冲击力强，主体明确。
    4. 第二、三张为信息海报：
       - 结构清晰，包含标题区、内容区。
       - 设计要求：模块化、文字排版清晰（提示词中描述排版逻辑）。
    
    严格返回JSON格式：
    {"images": [
      {"index": 1, "prompt": "封面图详细提示词(不包含“小红书”字样、Logo)", "title": "图片标题(不包含“小红书”字样、Logo)"},
      {"index": 2, "prompt": "海报1详细提示词(不包含“小红书”字样、Logo)", "title": "图片标题(不包含“小红书”字样、Logo)"},
      {"index": 3, "prompt": "海报2详细提示词(不包含“小红书”字样、Logo)", "title": "图片标题(不包含“小红书”字样、Logo)"}
    ]}
    """
    image_user_prompt = f"选定标题：{content_data['title']}\n文案内容：{content_data['copy']}"
    image_json_str = _call_llm(image_system_prompt, image_user_prompt)
    image_data = json.loads(image_json_str)
    
    # 整合结果
    final_result = {
        "images": image_data['images'],
        "title": content_data['title'],
        "copy": content_data['copy'],
        "tags": content_data['tags'],
        "planning_direction": best_direction
    }

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_prompt_path = os.path.join(OUTPUT_DIR, f"prompt_{timestamp}.json")
        with open(local_prompt_path, "w", encoding="utf-8") as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)
        
        tos_prompt_url = upload_to_tos(local_prompt_path, f"xiaohongshu/prompts/prompt_{timestamp}.json")
        final_result["tos_url"] = tos_prompt_url
        
        os.remove(local_prompt_path)
        print(f"✅ 图文prompt全流程生成并上传完成: {tos_prompt_url}")
        return final_result
    except Exception as e:
        print(f"❌ 结果保存失败: {str(e)}")
        raise

