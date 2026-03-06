#!/usr/bin/env python3
import sys
import os
import json

scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, scripts_dir)

from volc_engine_client import VolcEngineAI
from database import init_db
from generate_content_real import (
    qa_inspector_agent,
    clean_json_response,
    sanitize_filename
)

print("🎬 ===== 质检智能体测试 =====\n")

def main():
    print("===== 步骤 1: 初始化 =====")
    init_db()
    volc_ai = VolcEngineAI()
    
    # 先生成一张测试图片
    print("\n===== 步骤 2: 生成测试图片 =====")
    test_prompt = "JK少女在走廊里，月光，动漫风格"
    print(f"图片提示词: {test_prompt}")
    img_url = volc_ai.text_to_image(test_prompt)
    print(f"✅ 图片生成成功: {img_url[:80]}...\n")
    
    # 测试质检
    print("===== 步骤 3: 质检智能体检查 =====")
    qa_result = qa_inspector_agent(
        volc_ai,
        first_frame_url=img_url,
        ref_image_urls=[],
        image_prompt=test_prompt,
        max_retries=1
    )
    
    print(f"\n===== 质检结果 =====\n{json.dumps(qa_result, ensure_ascii=False, indent=2)}")
    
    print("\n✅ 质检智能体测试完成！")

if __name__ == "__main__":
    main()
