import time
import functools
from volcenginesdkarkruntime import Ark

from adsflow.config import (
    ARK_API_KEY,
    ARK_BASE_URL,
    SEEDANCE_MODEL_ID,
    SEEDREAM_MODEL_ID,
    VLM_MODEL_ID,
    POLL_INTERVAL,
    POLL_TIMEOUT,
)
from adsflow.logger import logger


def _retry_with_backoff(max_retries: int = 3, base_delay: float = 2.0):
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
                        logger.warning(
                            f"{func.__name__} 第 {attempt + 1} 次重试，"
                            f"错误: {exc}，{delay:.1f}s 后重试"
                        )
                        time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator


class SeedanceClient:
    """Seedance 2.0 + Seedream 5.0 客户端。

    封装 VLM 对话、图片识别、图生图、视频生成、视频编辑等能力。
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        seedance_model: str | None = None,
        seedream_model: str | None = None,
        vlm_model: str | None = None,
    ):
        self._api_key = api_key or ARK_API_KEY
        self._base_url = base_url or ARK_BASE_URL
        self._seedance_model = seedance_model or SEEDANCE_MODEL_ID
        self._seedream_model = seedream_model or SEEDREAM_MODEL_ID
        self._vlm_model = vlm_model or VLM_MODEL_ID
        self._client = Ark(api_key=self._api_key, base_url=self._base_url)
        logger.info(
            f"SeedanceClient 初始化完成，"
            f"视频模型: {self._seedance_model}，"
            f"图片模型: {self._seedream_model}，"
            f"VLM模型: {self._vlm_model}"
        )

    @property
    def client(self) -> Ark:
        return self._client

    # ── VLM 对话 ──

    @_retry_with_backoff(max_retries=3, base_delay=2.0)
    def chat(self, messages: list[dict], model: str | None = None, **kwargs) -> str:
        """VLM 多轮对话，返回文本响应。"""
        resolved_model = model or self._vlm_model
        response = self._client.chat.completions.create(
            model=resolved_model,
            messages=messages,
            **kwargs,
        )
        return response.choices[0].message.content

    def analyze_video(self, video_url: str, prompt: str, model: str | None = None) -> str:
        """使用 VLM 分析视频内容（通过 URL 传入视频）。"""
        resolved_model = model or self._vlm_model
        messages = [{
            "role": "user",
            "content": [
                {"type": "video_url", "video_url": {"url": video_url}},
                {"type": "text", "text": prompt},
            ],
        }]
        return self.chat(messages, model=resolved_model)

    def analyze_image(self, image_url: str, prompt: str, model: str | None = None) -> str:
        """使用 VLM 分析图片内容（通过 URL 传入图片）。"""
        resolved_model = model or self._vlm_model
        messages = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": prompt},
            ],
        }]
        return self.chat(messages, model=resolved_model)

    def compare_videos(
        self, video_url_1: str, video_url_2: str, prompt: str, model: str | None = None
    ) -> str:
        """使用 VLM 对比两个视频，返回对比分析结果。"""
        resolved_model = model or self._vlm_model
        messages = [{
            "role": "user",
            "content": [
                {"type": "video_url", "video_url": {"url": video_url_1}},
                {"type": "video_url", "video_url": {"url": video_url_2}},
                {"type": "text", "text": prompt},
            ],
        }]
        return self.chat(messages, model=resolved_model)

    # ── Seedream 5.0 图生图 ──

    @_retry_with_backoff(max_retries=2, base_delay=3.0)
    def image_to_image(
        self,
        prompt: str,
        reference_images: list[str] | str,
        model: str | None = None,
        size: str = "2048x2048",
        watermark: bool = False,
    ) -> str:
        """Seedream 5.0 图生图，返回生成图片 URL。

        用于处理真人替换图片：VLM 识别为真人后，用 Seedream 5.0 重新生成合规图片。
        """
        resolved_model = model or self._seedream_model
        if isinstance(reference_images, str):
            reference_images = [reference_images]

        logger.info(
            f"Seedream 图生图，模型: {resolved_model}，"
            f"参考图数: {len(reference_images)}，提示词: {prompt[:80]}..."
        )
        response = self._client.images.generate(
            model=resolved_model,
            prompt=prompt,
            image=reference_images,
            response_format="url",
            size=size,
            watermark=watermark,
        )
        url = response.data[0].url
        logger.info(f"Seedream 图生图完成，URL: {url[:80]}...")
        return url

    # ── Seedance 2.0 视频生成 ──

    def _poll_task(self, task_id: str, timeout: int = POLL_TIMEOUT) -> str:
        """轮询视频生成任务状态，直到成功或失败，返回视频 URL。"""
        start = time.time()
        while time.time() - start < timeout:
            result = self._client.content_generation.tasks.get(task_id=task_id)
            status = result.status
            if status == "succeeded":
                video_url = self._extract_video_url(result)
                logger.info(f"视频任务 {task_id} 成功，URL: {video_url}")
                return video_url
            elif status == "failed":
                error_msg = result.error.message if result.error else "Unknown error"
                raise RuntimeError(f"Seedance 任务失败: {error_msg}")
            elif status == "expired":
                raise RuntimeError(f"Seedance 任务过期: {task_id}")
            else:
                elapsed = time.time() - start
                logger.info(f"视频任务 {task_id} 状态: {status}，已耗时: {elapsed:.0f}s")
                time.sleep(POLL_INTERVAL)
        raise TimeoutError(f"Seedance 任务超时 ({timeout}s): {task_id}")

    @staticmethod
    def _extract_video_url(result) -> str | None:
        """从任务结果中提取视频 URL，兼容多种返回格式。"""
        if hasattr(result, "content") and result.content:
            if hasattr(result.content, "video_url"):
                return result.content.video_url
            if isinstance(result.content, dict) and "video_url" in result.content:
                return result.content["video_url"]
        if hasattr(result, "video_url"):
            return result.video_url
        try:
            data = result.model_dump()
            if "content" in data and isinstance(data["content"], dict):
                return data["content"].get("video_url")
            return data.get("video_url")
        except Exception:
            return None

    @_retry_with_backoff(max_retries=2, base_delay=5.0)
    def generate_video(
        self,
        prompt: str,
        reference_images: list[str] | None = None,
        reference_video: str | None = None,
        reference_audio: str | None = None,
        first_frame: str | None = None,
        last_frame: str | None = None,
        duration: int = 10,
        ratio: str = "16:9",
        resolution: str = "720p",
        generate_audio: bool = True,
        watermark: bool = False,
        model: str | None = None,
    ) -> str:
        """生成视频（多模态参考模式），返回视频 URL。

        Seedance 2.0 支持三种内容输入方式：
        - reference_images / reference_video / reference_audio：多模态参考
        - first_frame / last_frame：首尾帧控制
        - 纯文本 prompt：文生视频
        """
        resolved_model = model or self._seedance_model
        content: list[dict] = [{"type": "text", "text": prompt}]

        if first_frame:
            content.append({
                "type": "image_url",
                "image_url": {"url": first_frame},
                "role": "first_frame",
            })
        if last_frame:
            content.append({
                "type": "image_url",
                "image_url": {"url": last_frame},
                "role": "last_frame",
            })
        if reference_images:
            for img_url in reference_images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": img_url},
                    "role": "reference_image",
                })
        if reference_video:
            content.append({
                "type": "video_url",
                "video_url": {"url": reference_video},
                "role": "reference_video",
            })
        if reference_audio:
            content.append({
                "type": "audio_url",
                "audio_url": {"url": reference_audio},
                "role": "reference_audio",
            })

        logger.info(
            f"创建视频生成任务，模型: {resolved_model}，"
            f"时长: {duration}s，比例: {ratio}，内容项数: {len(content)}"
        )
        create_result = self._client.content_generation.tasks.create(
            model=resolved_model,
            content=content,
            generate_audio=generate_audio,
            ratio=ratio,
            resolution=resolution,
            duration=duration,
            watermark=watermark,
        )
        task_id = create_result.id
        logger.info(f"视频生成任务已创建，task_id: {task_id}")
        return self._poll_task(task_id)

    @_retry_with_backoff(max_retries=2, base_delay=5.0)
    def edit_video(
        self,
        prompt: str,
        reference_video: str,
        reference_images: list[str] | None = None,
        duration: int = 10,
        ratio: str = "16:9",
        generate_audio: bool = True,
        watermark: bool = False,
        model: str | None = None,
    ) -> str:
        """编辑视频（替换主体、增删改元素等），返回视频 URL。"""
        resolved_model = model or self._seedance_model
        content: list[dict] = [{"type": "text", "text": prompt}]

        if reference_images:
            for img_url in reference_images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": img_url},
                    "role": "reference_image",
                })

        content.append({
            "type": "video_url",
            "video_url": {"url": reference_video},
            "role": "reference_video",
        })

        logger.info(
            f"创建视频编辑任务，模型: {resolved_model}，"
            f"时长: {duration}s，参考视频: {reference_video[:80]}..."
        )
        create_result = self._client.content_generation.tasks.create(
            model=resolved_model,
            content=content,
            generate_audio=generate_audio,
            ratio=ratio,
            duration=duration,
            watermark=watermark,
        )
        task_id = create_result.id
        logger.info(f"视频编辑任务已创建，task_id: {task_id}")
        return self._poll_task(task_id)
