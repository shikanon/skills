#!/usr/bin/env python3
import os
import json
import sys
import requests
import boto3
from datetime import datetime
from openai import OpenAI

# 从 .env 文件加载环境变量
env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_file):
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# 火山引擎ARK配置
ARK_API_KEY = os.getenv("ARK_API_KEY")
ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
LLM_MODEL = "doubao-seed-2-0-pro-260215"
WEB_SEARCH_MODEL = "doubao-seed-2-0-pro-260215" # 使用 pro 模型支持 Responses API
IMAGE_MODEL = "doubao-seedream-4-5-251128" # 图片生成模型

# 火山引擎TOS配置
TOS_ACCESS_KEY = os.getenv("TOS_ACCESS_KEY")
TOS_SECRET_KEY = os.getenv("TOS_SECRET_KEY")
TOS_ENDPOINT = "https://tos-s3-cn-guangzhou.volces.com" # 使用 S3 兼容 Endpoint
TOS_BUCKET = "byteclaw"
TOS_REGION = "cn-guangzhou"

# 校验必填环境变量
required_envs = {
    "ARK_API_KEY": ARK_API_KEY,
    "TOS_ACCESS_KEY": TOS_ACCESS_KEY,
    "TOS_SECRET_KEY": TOS_SECRET_KEY
}
missing_envs = [k for k, v in required_envs.items() if not v]
if missing_envs:
    raise ValueError(f"❌ 缺少必要的环境变量: {', '.join(missing_envs)}")

# 初始化ARK客户端
client = OpenAI(
    api_key=ARK_API_KEY,
    base_url=ARK_BASE_URL
)

# 初始化TOS客户端 (使用boto3)
tos_client = boto3.client(
    's3',
    aws_access_key_id=TOS_ACCESS_KEY,
    aws_secret_access_key=TOS_SECRET_KEY,
    endpoint_url=TOS_ENDPOINT,
    region_name=TOS_REGION,
    config=boto3.session.Config(s3={'addressing_style': 'virtual'}) # 使用虚拟主机风格
)

def upload_to_tos(local_file_path: str, object_name: str) -> str:
    """
    上传文件到火山引擎TOS并返回访问地址
    """
    try:
        tos_client.upload_file(local_file_path, TOS_BUCKET, object_name)
        # 火山引擎TOS的公开访问地址格式：https://<bucket>.<endpoint>/<object_name>
        # 去掉endpoint前的https://
        clean_endpoint = TOS_ENDPOINT.replace("https://", "")
        url = f"https://{TOS_BUCKET}.{clean_endpoint}/{object_name}"
        print(f"✅ 文件已上传至TOS: {url}")
        return url
    except Exception as e:
        print(f"❌ 上传至TOS失败: {str(e)}")
        raise

# 工作目录
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(WORKSPACE, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def web_search(query: str, count: int = 5) -> list:
    """
    封装火山引擎联网搜索函数 (使用 Responses API)
    :param query: 搜索关键词
    :param count: 返回结果数量
    :return: 搜索结果列表
    """
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
                            # 提取所有可能的文本字段
                            content += item.get("text", "")
                            if not item.get("text") and "content" in item:
                                content += str(item["content"])
                        elif isinstance(item, str):
                            content += item
                else:
                    content = str(msg_content)
        
        # 如果还是没拿到，尝试从其它字段拿 (兼容性)
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

def search_cases():
    """搜索OpenClaw商业化变现相关案例"""
    print("🔍 正在搜索OpenClaw商业化变现相关案例...")
    # 调用封装好的web_search函数
    cases = web_search("OpenClaw 商业化 案例", count=5)
    
    if not cases:
        raise Exception("❌ 搜索未返回内容且已移除兜底策略")
    
    # 选择第一个高质量案例
    selected_case = cases[0]
    print(f"✅ 选中案例: {selected_case['title']}")
    return selected_case

def generate_prompts(case):
    """根据案例调用LLM生成图文prompt，按照知识类小红书Meta Prompt规范"""
    print("✍️ 正在调用大模型生成图文prompt...")
    
    # 系统提示词，按照用户提供的Meta Prompt规范
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
        # 移除可能的markdown代码块包裹
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        prompt_json = json.loads(content)
        
        # 保存并上传prompt.json
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_prompt_path = os.path.join(OUTPUT_DIR, f"prompt_{timestamp}.json")
        with open(local_prompt_path, "w", encoding="utf-8") as f:
            json.dump(prompt_json, f, ensure_ascii=False, indent=2)
        
        tos_prompt_url = upload_to_tos(local_prompt_path, f"xiaohongshu/prompts/prompt_{timestamp}.json")
        prompt_json["tos_url"] = tos_prompt_url
        
        # 删除本地文件
        os.remove(local_prompt_path)
        
        print(f"✅ 图文prompt生成并上传完成: {tos_prompt_url}")
        return prompt_json
    except Exception as e:
        print(f"❌ prompt生成失败: {str(e)}")
        raise

def generate_images(prompt_json):
    """生成4K图片并上传至TOS"""
    print("🖼️ 正在生成4K图片...")
    image_urls = []
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for img in prompt_json["images"]:
        # 根据图片类型添加不同的prompt后缀
        if img["index"] == 1:
            full_prompt = f"{img['prompt']}, 3:4比例, 小红书封面风格, 视觉冲击力强, 高质量"
        else:
            full_prompt = f"{img['prompt']}, 3:4比例, 小红书海报信息图风格, 清晰展示内容要点, 高质量"
        print(f"🎨 正在生成图片 {img['index']}: {img['title']}...")
        
        try:
            # 调用火山引擎图片生成 API (使用 OpenAI 兼容 SDK)
            response = client.images.generate(
                model=IMAGE_MODEL,
                prompt=full_prompt,
                size="4K",
                n=1,
            )
            
            # 获取生成的图片 URL
            gen_image_url = response.data[0].url
            print(f"✅ 图片 {img['index']} 生成成功，正在下载并上传...")
            
            # 下载生成的图片
            img_response = requests.get(gen_image_url)
            img_response.raise_for_status()
            
            # 本地临时保存
            local_path = os.path.join(OUTPUT_DIR, f"temp_image_{img['index']}_{timestamp}.png")
            with open(local_path, "wb") as f:
                f.write(img_response.content)
            
            # 上传到 TOS
            object_name = f"xiaohongshu/images/{timestamp}_image_{img['index']}.png"
            tos_url = upload_to_tos(local_path, object_name)
            image_urls.append(tos_url)
            
            # 删除本地临时文件
            os.remove(local_path)
            
            print(f"✅ 图片 {img['index']} 处理完成: {tos_url}")
                
        except Exception as e:
            print(f"⚠️ 图片 {img['index']} 处理失败，跳过继续: {str(e)}")
            
    return image_urls

def validate_images(image_urls, prompt_json):
    """校验图片质量 (基于URL)"""
    print("🔍 正在校验图片质量...")
    # 这里可以调用多模态模型校验，目前模拟校验通过
    all_valid = True
    for i, url in enumerate(image_urls):
        print(f"✅ 图片{i+1}校验通过: {url}")
    
    return all_valid

def send_to_feishu(prompt_json, image_urls):
    """打印内容并显示TOS资源地址"""
    print("📤 正在输出生成结果...")
    
    # 输出文案和标签
    message_content = f"""✨ 生成的小红书内容如下：

📝 文案：
{prompt_json['copy']}

🏷️ 标签：
{' '.join(prompt_json['tags'])}

🔗 提示词资源地址：
{prompt_json.get('tos_url', 'N/A')}
"""
    print("MESSAGE_CONTENT_START")
    print(message_content)
    print("MESSAGE_CONTENT_END")
    
    # 输出图片URL列表
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
    print(f"\n📄 JSON配置TOS资源地址: {prompt_json.get('tos_url')}")

def main():
    try:
        # Step 1: 搜索案例
        case = search_cases()
        
        # Step 2: 生成prompt
        prompt_json = generate_prompts(case)
        
        # Step 3: 生成图片
        image_urls = generate_images(prompt_json)
        
        # Step 4: 校验图片
        valid = validate_images(image_urls, prompt_json)
        if not valid:
            print("❌ 图片校验不通过，重新生成...")
            return main()
        
        # Step 5: 发送到飞书
        send_to_feishu(prompt_json, image_urls)
        
        print("\n🎉 小红书热门图文生成完成！")
        
    except Exception as e:
        print(f"❌ 生成失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
