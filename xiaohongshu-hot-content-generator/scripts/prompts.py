#!/usr/bin/env python3
import json
import os
from datetime import datetime
from config import client, OUTPUT_DIR, LLM_MODEL
from uploader import upload_to_tos

def generate_prompts(case):
    print("✍️ 正在调用大模型生成图文prompt...")
    
    system_prompt = """
你是小红书爆款策划师，严格返回JSON格式，包含三个字段：
- images: 数组，每个元素有index(序号)、prompt(图片描述)、title(小标题)，共3张图。
  第一张为封面图：视觉冲击力强
  第二、三张为海报信息图，设计要求：
  1. 标题吸睛：主标题15字内，带情绪感/干货感/热点感（emoji≤2），副标题8-12字突出核心价值（如"新手必看""3步搞定""干货收藏"）
  2. 结构适配竖版海报：分2-4个核心模块，每模块有5-8字加粗感小标题，拒绝大段文字
  3. 内容极简：每模块3-4条内容，全用短句（10字内）、关键词、阿拉伯数字，不用长句和复杂描述
  4. 视觉适配：自带海报作图逻辑，模块清晰、错落有致，对应"标题区-核心内容区-结尾引导区"
- copy: 小红书文案，口语化，有emoji，开头吸睛，中间分点，结尾引导互动
- tags: 数组，6-10个标签，相关热门标签
不要返回任何其他内容，只返回JSON。
"""
    
    user_prompt = f"基于以下案例生成小红书图文内容：\n案例标题：{case['title']}\n案例内容：{case['content']}"
    
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
        content = content.strip()
        
        prompt_json = json.loads(content)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_prompt_path = os.path.join(OUTPUT_DIR, f"prompt_{timestamp}.json")
        with open(local_prompt_path, "w", encoding="utf-8") as f:
            json.dump(prompt_json, f, ensure_ascii=False, indent=2)
        
        tos_prompt_url = upload_to_tos(local_prompt_path, f"xiaohongshu/prompts/prompt_{timestamp}.json")
        prompt_json["tos_url"] = tos_prompt_url
        
        os.remove(local_prompt_path)
        
        print(f"✅ 图文prompt生成并上传完成: {tos_prompt_url}")
        return prompt_json
    except Exception as e:
        print(f"❌ prompt生成失败: {str(e)}")
        raise

