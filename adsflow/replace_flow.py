import json
import os
import time
import shutil
import urllib.request
from dataclasses import dataclass, field

from adsflow.seedance_client import SeedanceClient
from adsflow.ffmpeg_ops import (
    get_video_duration,
    slice_video,
    concat_videos,
)
from adsflow.templates import (
    IMAGE_IDENTIFY_PROMPT,
    SEEDREAM_REGENERATE_PROMPT,
    SEEDANCE_REPLACE_PROMPT,
    VIDEO_COMPARE_PROMPT,
)
from adsflow.config import SEEDANCE_MAX_DURATION, SLICE_DURATION, OUTPUT_DIR
from adsflow.logger import logger


def _clean_json_response(text: str) -> str:
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return text


def _parse_json(text: str) -> dict:
    return json.loads(_clean_json_response(text))


@dataclass
class SliceInfo:
    """单个视频切片的信息。"""
    path: str
    url: str
    duration: int


@dataclass
class ReplaceFlowConfig:
    """爆款裂变工作流配置。"""
    video_path: str
    replace_images: list[str] = field(default_factory=list)
    replace_requirement: str = ""
    slice_duration: int = SLICE_DURATION
    ratio: str = "16:9"
    resolution: str = "720p"
    generate_audio: bool = True
    watermark: bool = False
    compare_check_enabled: bool = True
    compare_pass_threshold: float = 7.0
    max_compare_retries: int = 2
    output_dir: str = OUTPUT_DIR


class ReplaceFlow:
    """爆款裂变工作流：将长广告视频中的产品/元素替换为用户指定内容。

    核心流程：
    Step 0: 视频切片检查 → 超过15秒自动切片，记录每个切片时长（四舍五入取整）
    Step 1: VLM 识别替换图片 → 真人图片用 Seedream 5.0 图生图重新生成
    Step 2: Seedance 视频生成 → 输入参考视频（切片）+ 参考图 + 替换要求 + 视频时长
    Step 3: 两个视频对比检查替换效果
    Step 4: 视频拼接 → 多片段合并为最终视频
    """

    def __init__(self, client: SeedanceClient, config: ReplaceFlowConfig):
        self._client = client
        self._config = config
        os.makedirs(config.output_dir, exist_ok=True)

    def run(self) -> str:
        logger.info("=" * 60)
        logger.info("🚀 爆款裂变工作流 (ReplaceFlow) 启动")
        logger.info(f"📹 原始视频: {self._config.video_path}")
        logger.info(f"🖼️ 替换图片数: {len(self._config.replace_images)}")
        logger.info(f"📝 替换要求: {self._config.replace_requirement}")
        logger.info("=" * 60)

        start_time = time.time()

        try:
            # Step 0: 视频切片
            slices = self._step_slice_video()

            # Step 1: VLM 识别替换图片 + 真人图片处理
            processed_images = self._step_identify_images()

            # Step 2 + 3: 对每个切片生成替换视频 + 对比检查
            segment_paths = self._process_all_slices(slices, processed_images)

            # Step 4: 视频拼接
            final_path = self._step_concat(segment_paths)

            elapsed = time.time() - start_time
            logger.info("=" * 60)
            logger.info(f"✅ 爆款裂变工作流完成！耗时: {elapsed:.1f}s")
            logger.info(f"🎞️ 最终视频: {final_path}")
            logger.info("=" * 60)
            return final_path

        except Exception as exc:
            logger.error(f"❌ 爆款裂变工作流失败: {exc}")
            raise

    # ── Step 0: 视频切片检查 ──

    def _step_slice_video(self) -> list[SliceInfo]:
        """视频切片检查：超过15秒自动切片，记录每个切片时长（四舍五入取整）。"""
        logger.info("📋 Step 0: 视频切片检查")
        video_path = self._config.video_path

        if video_path.startswith(("http://", "https://")):
            logger.info("  远程视频 URL，无法本地切片，整体作为一个片段处理")
            logger.info("  ⚠️ 建议提供本地视频路径以启用切片功能")
            return [SliceInfo(
                path=video_path,
                url=video_path,
                duration=SEEDANCE_MAX_DURATION,
            )]

        duration = get_video_duration(video_path)
        rounded_duration = round(duration)
        logger.info(f"  视频时长: {duration:.2f}s（四舍五入: {rounded_duration}s）")

        if duration <= self._config.slice_duration:
            logger.info("  视频时长未超过切片阈值，无需切片")
            return [SliceInfo(
                path=video_path,
                url=video_path,
                duration=rounded_duration,
            )]

        slice_dir = os.path.join(self._config.output_dir, "slices")
        slice_paths = slice_video(video_path, self._config.slice_duration, output_dir=slice_dir)

        slices = []
        for i, sp in enumerate(slice_paths):
            seg_duration = get_video_duration(sp)
            rounded_seg = round(seg_duration)
            logger.info(f"  片段 {i}: {sp}，时长: {seg_duration:.2f}s → {rounded_seg}s")
            slices.append(SliceInfo(
                path=sp,
                url=sp,
                duration=rounded_seg,
            ))

        logger.info(f"  切片完成，共 {len(slices)} 个片段")
        return slices

    # ── Step 1: VLM 识别替换图片 ──

    def _step_identify_images(self) -> list[str]:
        """VLM 识别替换图片：真人图片用 Seedream 5.0 图生图重新生成。"""
        logger.info("🔍 Step 1: VLM 识别替换图片")
        images = self._config.replace_images
        if not images:
            logger.info("  无替换图片，跳过此步骤")
            return []

        processed = []
        for i, img_url in enumerate(images):
            logger.info(f"  识别图片 {i + 1}/{len(images)}: {img_url[:80]}...")

            try:
                response = self._client.analyze_image(img_url, IMAGE_IDENTIFY_PROMPT)
                result = _parse_json(response)
                is_real_person = result.get("is_real_person", False)
                description = result.get("description", "")
                logger.info(f"    识别结果: 真人={is_real_person}，描述={description[:100]}")

                if is_real_person:
                    logger.info(f"    ⚠️ 检测到真人图片，使用 Seedream 5.0 重新生成")
                    new_url = self._regenerate_image(img_url, description)
                    processed.append(new_url)
                    logger.info(f"    ✅ Seedream 重新生成完成: {new_url[:80]}...")
                else:
                    logger.info(f"    ✅ 非真人图片，直接使用")
                    processed.append(img_url)

            except json.JSONDecodeError:
                logger.warning(f"    图片识别结果解析失败，默认直接使用")
                processed.append(img_url)
            except Exception as exc:
                logger.warning(f"    图片识别失败: {exc}，默认直接使用")
                processed.append(img_url)

        return processed

    def _regenerate_image(self, original_url: str, description: str) -> str:
        """使用 Seedream 5.0 图生图重新生成合规图片。

        如果 Seedream 不可用（如模型未开通），降级为直接使用原始图片。
        """
        prompt = SEEDREAM_REGENERATE_PROMPT.format(
            image_description=description,
            replace_requirement=self._config.replace_requirement,
        )
        try:
            return self._client.image_to_image(
                prompt=prompt,
                reference_images=original_url,
            )
        except Exception as exc:
            logger.warning(f"    Seedream 图生图失败: {exc}")
            logger.warning(f"    降级处理：直接使用原始图片")
            return original_url

    # ── Step 2 + 3: 对每个切片生成替换视频 + 对比检查 ──

    def _process_all_slices(
        self, slices: list[SliceInfo], processed_images: list[str]
    ) -> list[str]:
        """对每个切片执行：提示词生成 → 视频生成 → 对比检查。"""
        all_segment_paths = []

        for i, slice_info in enumerate(slices):
            logger.info(f"\n{'=' * 50}")
            logger.info(f"🎬 处理片段 {i + 1}/{len(slices)}，时长: {slice_info.duration}s")
            logger.info(f"{'=' * 50}")

            # Step 2: Seedance 视频生成
            video_url = self._step_seedance_generate(slice_info, processed_images)

            # Step 3: 视频对比检查
            if self._config.compare_check_enabled:
                video_url = self._step_compare_check(
                    video_url, slice_info, processed_images
                )

            # 下载到本地
            output_path = os.path.join(
                self._config.output_dir, f"segment_{i:03d}.mp4"
            )
            local_path = self._download_if_remote(video_url, output_path)
            all_segment_paths.append(local_path)

        return all_segment_paths

    def _step_seedance_generate(
        self, slice_info: SliceInfo, processed_images: list[str]
    ) -> str:
        """Step 2: Seedance 视频生成。

        输入：参考视频（切片）+ 参考图 + 替换要求 + 视频时长
        """
        logger.info("🎬 Step 2: Seedance 视频生成")

        # 生成提示词
        prompt_text = self._build_seedance_prompt(slice_info, processed_images)

        effective_duration = max(4, min(slice_info.duration, SEEDANCE_MAX_DURATION))

        return self._client.generate_video(
            prompt=prompt_text,
            reference_images=processed_images or None,
            reference_video=slice_info.url,
            duration=effective_duration,
            ratio=self._config.ratio,
            resolution=self._config.resolution,
            generate_audio=self._config.generate_audio,
            watermark=self._config.watermark,
        )

    def _build_seedance_prompt(
        self, slice_info: SliceInfo, processed_images: list[str]
    ) -> str:
        """构建 Seedance 视频生成提示词。"""
        prompt_template = SEEDANCE_REPLACE_PROMPT.format(
            duration=slice_info.duration,
            replace_requirement=self._config.replace_requirement,
        )
        messages = [{"role": "user", "content": prompt_template}]
        response = self._client.chat(messages)

        try:
            result = _parse_json(response)
            generated_prompt = result.get("prompt", "")
            if generated_prompt:
                key_changes = result.get("key_changes", [])
                if key_changes:
                    logger.info(f"  关键替换点: {', '.join(key_changes[:3])}")
                return generated_prompt
        except json.JSONDecodeError:
            pass

        logger.warning("  提示词生成结果非标准 JSON，使用替换要求作为提示词")
        return self._config.replace_requirement

    def _step_compare_check(
        self,
        new_video_url: str,
        slice_info: SliceInfo,
        processed_images: list[str],
    ) -> str:
        """Step 3: 两个视频对比检查替换效果。"""
        logger.info("🔎 Step 3: 视频对比检查")

        for attempt in range(self._config.max_compare_retries + 1):
            try:
                response = self._client.compare_videos(
                    video_url_1=slice_info.url,
                    video_url_2=new_video_url,
                    prompt=VIDEO_COMPARE_PROMPT,
                )
                result = _parse_json(response)
                overall_score = result.get("overall_score", 0)
                passed = result.get("passed", overall_score >= self._config.compare_pass_threshold)
                issues = result.get("issues", [])

                logger.info(f"  对比评分: {overall_score:.1f}/10，通过: {passed}")
                if issues:
                    logger.info(f"  问题: {', '.join(str(i) for i in issues[:3])}")

                if passed:
                    return new_video_url

                if attempt < self._config.max_compare_retries:
                    improved_prompt = result.get("improved_prompt", "")
                    if improved_prompt:
                        logger.info(f"  对比未通过，使用改进提示词重新生成 (第 {attempt + 1} 次重试)")
                        effective_duration = max(4, min(slice_info.duration, SEEDANCE_MAX_DURATION))
                        new_video_url = self._client.generate_video(
                            prompt=improved_prompt,
                            reference_images=processed_images or None,
                            reference_video=slice_info.url,
                            duration=effective_duration,
                            ratio=self._config.ratio,
                            resolution=self._config.resolution,
                            generate_audio=self._config.generate_audio,
                            watermark=self._config.watermark,
                        )
                        continue
                    else:
                        logger.warning("  对比未通过但未提供改进提示词，保留当前结果")
                        return new_video_url
                else:
                    logger.warning(
                        f"  对比未通过且已达最大重试次数 ({self._config.max_compare_retries})，保留当前结果"
                    )
                    return new_video_url

            except json.JSONDecodeError:
                logger.warning("  对比结果解析失败，默认通过")
                return new_video_url
            except Exception as exc:
                logger.warning(f"  对比检查异常: {exc}，保留当前结果")
                return new_video_url

        return new_video_url

    # ── Step 4: 视频拼接 ──

    def _step_concat(self, segment_paths: list[str]) -> str:
        """Step 4: 视频拼接 → 多片段合并为最终视频。"""
        logger.info("🔗 Step 4: 视频拼接")
        if not segment_paths:
            raise ValueError("没有可拼接的视频片段")

        if len(segment_paths) == 1:
            final_path = os.path.join(self._config.output_dir, "final_replaced.mp4")
            if segment_paths[0] != final_path:
                shutil.copy2(segment_paths[0], final_path)
            return final_path

        final_path = os.path.join(self._config.output_dir, "final_replaced.mp4")
        return concat_videos(segment_paths, final_path)

    # ── 工具方法 ──

    @staticmethod
    def _download_if_remote(url_or_path: str, output_path: str) -> str:
        """如果是远程 URL 则下载到本地，否则直接复制。"""
        if not url_or_path.startswith(("http://", "https://")):
            if url_or_path != output_path:
                shutil.copy2(url_or_path, output_path)
            return output_path

        logger.info(f"  下载视频: {url_or_path[:80]}... -> {output_path}")
        urllib.request.urlretrieve(url_or_path, output_path)
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        logger.info(f"  下载完成: {output_path} ({file_size:.2f} MB)")
        return output_path
