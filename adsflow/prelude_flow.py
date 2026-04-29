import json
import os
import time
import tempfile
from dataclasses import dataclass, field

from adsflow.seedance_client import SeedanceClient
from adsflow.ffmpeg_ops import (
    get_video_duration,
    trim_video,
    extract_audio,
    add_audio_to_video,
    concat_videos,
)
from adsflow.config import SEEDANCE_MAX_DURATION, OUTPUT_DIR
from adsflow.logger import logger


VLM_PRELUDE_PROMPT = """你是一位专业的广告创意分析师。请分析以下广告视频，为前贴创意设计提供参考依据。

分析内容：
1. 视频的主题和核心信息
2. 视觉风格特征
3. 情感基调和目标受众
4. 已有的品牌元素

请以 JSON 格式输出：
{
  "theme": "视频主题",
  "core_message": "核心信息",
  "visual_style": "视觉风格描述",
  "emotional_tone": "情感基调",
  "target_audience": "目标受众",
  "brand_elements": ["品牌元素1", "品牌元素2"],
  "key_visual_motifs": ["视觉母题1", "视觉母题2"]
}"""

SEEDANCE_PRELUDE_PROMPT = """你是一位专业的 Seedance 视频提示词工程师。基于对原广告视频的分析，为前贴片段生成精准的英文提示词。

**原视频分析结果**：
{video_analysis}

**前贴时长**：{duration} 秒

前贴创意要求：
1. **开场冲击**：前1-2秒必须有强烈的视觉冲击力
2. **品牌露出**：在第3-5秒自然融入品牌元素
3. **悬念设置**：在结尾设置悬念，引导观众继续观看正片
4. **节奏紧凑**：每个镜头不超过2秒，保持快节奏
5. **情感共鸣**：在短时间内建立情感连接

请以 JSON 格式输出：
{{
  "prompt": "完整的英文前贴视频生成提示词",
  "shots": [
    {{
      "time_range": "0-2s",
      "description": "开场冲击画面描述",
      "camera": "镜头运动"
    }},
    {{
      "time_range": "2-5s",
      "description": "品牌露出画面描述",
      "camera": "镜头运动"
    }},
    {{
      "time_range": "5-{duration}s",
      "description": "悬念设置画面描述",
      "camera": "镜头运动"
    }}
  ],
  "style_notes": "整体风格说明"
}}"""


def _clean_json_response(text: str) -> str:
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return text


def _parse_json(text: str) -> dict:
    return json.loads(_clean_json_response(text))


@dataclass
class PreludeFlowConfig:
    """广告前贴工作流配置。"""
    video_path: str
    prelude_duration: int = 10
    ratio: str = "16:9"
    resolution: str = "720p"
    generate_audio: bool = True
    watermark: bool = False
    output_dir: str = OUTPUT_DIR


class PreludeFlow:
    """广告前贴工作流：为原广告视频生成一个吸引人的前贴片段，并将前贴与原视频合成。

    核心流程：
    1. VLM 分析视频内容
    2. 前贴提示词生成
    3. 生成前贴视频
    4. 切取原视频前 N 秒 + 抽取音频
    5. 音频和前贴视频合成
    6. 前贴视频与原视频合成
    """

    def __init__(self, client: SeedanceClient, config: PreludeFlowConfig):
        self._client = client
        self._config = config
        os.makedirs(config.output_dir, exist_ok=True)

    def run(self) -> str:
        """执行完整的广告前贴工作流，返回最终视频路径。"""
        prelude_duration = min(self._config.prelude_duration, SEEDANCE_MAX_DURATION)

        logger.info("=" * 60)
        logger.info("🎬 广告前贴工作流 (PreludeFlow) 启动")
        logger.info(f"📹 原始视频: {self._config.video_path}")
        logger.info(f"⏱️ 前贴时长: {prelude_duration}s")
        logger.info("=" * 60)

        start_time = time.time()

        try:
            video_url = self._prepare_video_url()
            analysis = self._step_vlm_analyze(video_url)
            generation = self._step_generate_prelude_prompt(analysis, prelude_duration)
            prelude_url = self._step_generate_prelude_video(generation, prelude_duration)

            prelude_local = self._download_or_use_local(
                prelude_url, os.path.join(self._config.output_dir, "prelude.mp4")
            )

            if self._config.video_path.startswith(("http://", "https://")):
                logger.info("  原视频为远程 URL，仅返回前贴视频")
                final_path = os.path.join(self._config.output_dir, "final_with_prelude.mp4")
                import shutil
                shutil.copy2(prelude_local, final_path)
                return final_path

            final_path = self._step_compose_with_original(prelude_local, prelude_duration)

            elapsed = time.time() - start_time
            logger.info("=" * 60)
            logger.info(f"✅ 广告前贴工作流完成！耗时: {elapsed:.1f}s")
            logger.info(f"🎞️ 最终视频: {final_path}")
            logger.info("=" * 60)
            return final_path

        except Exception as exc:
            logger.error(f"❌ 广告前贴工作流失败: {exc}")
            raise

    def _prepare_video_url(self) -> str:
        if self._config.video_path.startswith(("http://", "https://")):
            return self._config.video_path
        logger.info("⚠️ 本地视频路径，Seedance API 需要公网可访问的 URL")
        return self._config.video_path

    def _step_vlm_analyze(self, video_url: str) -> dict:
        """Step 0: VLM 分析视频内容。"""
        logger.info("🔍 Step 0: VLM 分析视频内容")
        response = self._client.analyze_video(video_url, VLM_PRELUDE_PROMPT)
        try:
            analysis = _parse_json(response)
            logger.info(f"  视频主题: {analysis.get('theme', 'N/A')}")
            return analysis
        except json.JSONDecodeError:
            logger.warning("  VLM 分析结果非标准 JSON，使用原始文本")
            return {"raw_analysis": response, "theme": "未知"}

    def _step_generate_prelude_prompt(self, analysis: dict, duration: int) -> dict:
        """Step 1: 前贴提示词生成。"""
        logger.info("✍️ Step 1: 前贴提示词生成")
        prompt = SEEDANCE_PRELUDE_PROMPT.format(
            video_analysis=json.dumps(analysis, ensure_ascii=False, indent=2),
            duration=duration,
        )
        messages = [{"role": "user", "content": prompt}]
        response = self._client.chat(messages)
        try:
            generation = _parse_json(response)
            logger.info(f"  前贴提示词生成完成，镜头数: {len(generation.get('shots', []))}")
            return generation
        except json.JSONDecodeError:
            logger.warning("  前贴提示词生成结果非标准 JSON，使用原始文本")
            return {"prompt": response, "shots": []}

    def _step_generate_prelude_video(self, generation: dict, duration: int) -> str:
        """Step 2: 生成前贴视频。"""
        logger.info("🎬 Step 2: 生成前贴视频")
        prompt_text = generation.get("prompt", "")
        if not prompt_text:
            prompt_text = json.dumps(generation, ensure_ascii=False)

        return self._client.generate_video(
            prompt=prompt_text,
            duration=duration,
            ratio=self._config.ratio,
            resolution=self._config.resolution,
            generate_audio=self._config.generate_audio,
            watermark=self._config.watermark,
        )

    def _step_compose_with_original(self, prelude_local: str, prelude_duration: int) -> str:
        """Step 3-5: 切取原视频前N秒+抽取音频→合成→拼接。"""
        video_path = self._config.video_path
        output_dir = self._config.output_dir

        total_duration = get_video_duration(video_path)
        logger.info(f"  原视频时长: {total_duration:.1f}s")

        head_path = os.path.join(output_dir, "head_segment.mp4")
        trim_video(video_path, 0, prelude_duration, head_path)

        head_audio_path = os.path.join(output_dir, "head_audio.aac")
        extract_audio(head_path, head_audio_path)

        prelude_with_audio_path = os.path.join(output_dir, "prelude_with_audio.mp4")
        add_audio_to_video(prelude_local, head_audio_path, prelude_with_audio_path)

        remaining_path = None
        if total_duration > prelude_duration:
            remaining_path = os.path.join(output_dir, "remaining.mp4")
            trim_video(video_path, prelude_duration, total_duration - prelude_duration, remaining_path)

        if remaining_path:
            final_path = os.path.join(output_dir, "final_with_prelude.mp4")
            return concat_videos([prelude_with_audio_path, remaining_path], final_path)
        else:
            final_path = os.path.join(output_dir, "final_with_prelude.mp4")
            import shutil
            shutil.copy2(prelude_with_audio_path, final_path)
            return final_path

    @staticmethod
    def _download_or_use_local(url_or_path: str, output_path: str) -> str:
        """如果是 URL 则下载，否则直接复制。"""
        if url_or_path.startswith(("http://", "https://")):
            import urllib.request
            logger.info(f"  下载视频: {url_or_path[:80]}... -> {output_path}")
            urllib.request.urlretrieve(url_or_path, output_path)
            return output_path
        if url_or_path != output_path:
            import shutil
            shutil.copy2(url_or_path, output_path)
        return output_path
