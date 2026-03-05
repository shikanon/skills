#!/usr/bin/env python3
import os
from config import tos_client, TOS_BUCKET, TOS_ENDPOINT

def upload_to_tos(local_file_path: str, object_name: str) -> str:
    try:
        tos_client.upload_file(local_file_path, TOS_BUCKET, object_name)
        clean_endpoint = TOS_ENDPOINT.replace("https://", "")
        url = f"https://{TOS_BUCKET}.{clean_endpoint}/{object_name}"
        print(f"✅ 文件已上传至TOS: {url}")
        return url
    except Exception as e:
        print(f"❌ 上传至TOS失败: {str(e)}")
        raise
