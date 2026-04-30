import base64
import functools
import time

from ui_tester.config import (
    ARK_API_KEY,
    ARK_BASE_URL,
    VLM_MODEL_ID,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL_ID,
)
from ui_tester.logger import logger


def _retry(max_retries: int = 3, base_delay: float = 2.0):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"{func.__name__} 第 {attempt + 1} 次重试: {exc}，{delay:.1f}s 后重试")
                        time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator


def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


class VLMClient:
    """多后端 VLM 客户端，支持火山方舟和 OpenAI。"""

    def __init__(self, backend: str | None = None):
        self._backend = backend or "volcengine"
        self._volcengine_client = None
        self._openai_client = None

    @property
    def backend(self) -> str:
        return self._backend

    def _get_volcengine(self):
        if self._volcengine_client is None:
            from volcenginesdkarkruntime import Ark
            self._volcengine_client = Ark(api_key=ARK_API_KEY, base_url=ARK_BASE_URL)
        return self._volcengine_client

    def _get_openai(self):
        if self._openai_client is None:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        return self._openai_client

    @_retry(max_retries=3, base_delay=2.0)
    def analyze_image(self, image_path: str, prompt: str) -> str:
        """分析图片，返回 VLM 文本响应。"""
        logger.info(f"VLM 分析图片: {image_path}，后端: {self._backend}")
        if self._backend == "volcengine":
            return self._analyze_volcengine(image_path, prompt)
        elif self._backend == "openai":
            return self._analyze_openai(image_path, prompt)
        else:
            raise ValueError(f"不支持的 VLM 后端: {self._backend}")

    def _analyze_volcengine(self, image_path: str, prompt: str) -> str:
        client = self._get_volcengine()
        b64 = _encode_image(image_path)
        # 火山方舟 VLM 支持 base64 图片输入
        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                },
                {"type": "text", "text": prompt},
            ],
        }]
        response = client.chat.completions.create(model=VLM_MODEL_ID, messages=messages)
        return response.choices[0].message.content

    def _analyze_openai(self, image_path: str, prompt: str) -> str:
        client = self._get_openai()
        b64 = _encode_image(image_path)
        response = client.chat.completions.create(
            model=OPENAI_MODEL_ID,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
            max_tokens=4096,
        )
        return response.choices[0].message.content
