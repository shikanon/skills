#!/usr/bin/env python3
import os
import boto3
from openai import OpenAI

env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_file):
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

ARK_API_KEY = os.getenv("ARK_API_KEY")
ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
LLM_MODEL = "doubao-seed-2-0-pro-260215"
WEB_SEARCH_MODEL = "doubao-seed-2-0-pro-260215"
IMAGE_MODEL = "doubao-seedream-4-5-251128"

TOS_ACCESS_KEY = os.getenv("TOS_ACCESS_KEY")
TOS_SECRET_KEY = os.getenv("TOS_SECRET_KEY")
TOS_ENDPOINT = "https://tos-s3-cn-guangzhou.volces.com"
TOS_BUCKET = "byteclaw"
TOS_REGION = "cn-guangzhou"

XIAOHONGSHU_COOKIES = os.getenv("XIAOHONGSHU_COOKIES")

required_envs = {
    "ARK_API_KEY": ARK_API_KEY,
    "TOS_ACCESS_KEY": TOS_ACCESS_KEY,
    "TOS_SECRET_KEY": TOS_SECRET_KEY
}
missing_envs = [k for k, v in required_envs.items() if not v]
if missing_envs:
    raise ValueError(f"❌ 缺少必要的环境变量: {', '.join(missing_envs)}")

client = OpenAI(
    api_key=ARK_API_KEY,
    base_url=ARK_BASE_URL
)

tos_client = boto3.client(
    's3',
    aws_access_key_id=TOS_ACCESS_KEY,
    aws_secret_access_key=TOS_SECRET_KEY,
    endpoint_url=TOS_ENDPOINT,
    region_name=TOS_REGION,
    config=boto3.session.Config(s3={'addressing_style': 'virtual'})
)

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(WORKSPACE, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

