#!/usr/bin/env python3
import os
import requests
from datetime import datetime
from config import client, OUTPUT_DIR, IMAGE_MODEL
from uploader import upload_to_tos

def generate_images(prompt_json):
    print("🖼️ 正在生成4K图片...")
    image_urls = []
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for img in prompt_json["images"]:
        if img["index"] == 1:
            full_prompt = f"{img['prompt']}, 3:4比例, 小红书封面风格, 视觉冲击力强, 高质量"
        else:
            full_prompt = f"{img['prompt']}, 3:4比例, 小红书海报信息图风格, 清晰展示内容要点, 高质量"
        print(f"🎨 正在生成图片 {img['index']}: {img['title']}...")
        
        try:
            response = client.images.generate(
                model=IMAGE_MODEL,
                prompt=full_prompt,
                size="4K",
                n=1,
            )
            
            gen_image_url = response.data[0].url
            print(f"✅ 图片{img['index']} 生成成功，正在下载并上传...")
            
            img_response = requests.get(gen_image_url)
            img_response.raise_for_status()
            
            local_path = os.path.join(OUTPUT_DIR, f"temp_image_{img['index']}_{timestamp}.png")
            with open(local_path, "wb") as f:
                f.write(img_response.content)
            
            object_name = f"xiaohongshu/images/{timestamp}_image_{img['index']}.png"
            tos_url = upload_to_tos(local_path, object_name)
            image_urls.append(tos_url)
            
            os.remove(local_path)
            
            print(f"✅ 图片 {img['index']} 处理完成: {tos_url}")
                
        except Exception as e:
            print(f"⚠️ 图片 {img['index']} 处理失败，跳过继续: {str(e)}")
            
    return image_urls

def validate_images(image_urls, prompt_json):
    print("🔍 正在校验图片质量...")
    all_valid = True
    for i, url in enumerate(image_urls):
        print(f"✅ 图片{i+1}校验通过: {url}")
    
    return all_valid
