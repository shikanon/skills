#!/usr/bin/env python3

def send_to_feishu(prompt_json, image_urls):
    print("📤 正在输出生成结果...")
    
    prompt_url = prompt_json.get('tos_url')
    prompt_url_display = prompt_url if prompt_url else "目前未成功上传到对象存储"
    
    message_content = f"""✨ 生成的小红书内容如下：

📝 文案：
{prompt_json['copy']}

🏷️ 标签：
{' '.join(prompt_json['tags'])}

🔗 提示词资源地址：
{prompt_url_display}
"""
    print("MESSAGE_CONTENT_START")
    print(message_content)
    print("MESSAGE_CONTENT_END")
    
    image_titles = [img["title"] for img in prompt_json["images"]]
    print("IMAGE_LIST_START")
    for i, (url, title) in enumerate(zip(image_urls, image_titles)):
        print(f"{url}|{title}")
    print("IMAGE_LIST_END")
    
    print("✅ 内容生成完成！所有资源已上传至火山引擎TOS。")
    print("\n📝 小红书文案:")
    print(prompt_json["copy"])
    print("\n🏷️ 标签:")
    print(" ".join(prompt_json["tags"]))
    print("\n🖼️ 图片TOS资源地址:")
    for url in image_urls:
        print(url)
    prompt_url_final = prompt_json.get('tos_url')
    prompt_url_final_display = prompt_url_final if prompt_url_final else "目前未成功上传到对象存储"
    print(f"\n📄 JSON配置TOS资源地址: {prompt_url_final_display}")
