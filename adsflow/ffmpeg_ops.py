import os
import subprocess
import json
import tempfile

from adsflow.logger import logger


def get_video_duration(video_path: str) -> float:
    """使用 ffprobe 获取视频时长（秒）。"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        return float(result.stdout.strip())
    raise RuntimeError(f"获取视频时长失败: {result.stderr}")


def get_video_info(video_path: str) -> dict:
    """使用 ffprobe 获取视频详细信息（时长、宽高、帧率等）。"""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration:format=duration",
        "-of", "json",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return json.loads(result.stdout)
    raise RuntimeError(f"获取视频信息失败: {result.stderr}")


def slice_video(video_path: str, slice_duration: int, output_dir: str | None = None) -> list[str]:
    """将视频按指定时长切片，返回切片文件路径列表。

    如果视频时长不超过 slice_duration，直接返回原视频路径。
    """
    duration = get_video_duration(video_path)
    if duration <= slice_duration:
        logger.info(f"视频时长 {duration:.1f}s 未超过切片阈值 {slice_duration}s，无需切片")
        return [video_path]

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="adsflow_slice_")
    os.makedirs(output_dir, exist_ok=True)

    num_slices = int(duration // slice_duration)
    if duration % slice_duration > 0.5:
        num_slices += 1

    slice_paths = []
    for i in range(num_slices):
        start_time = i * slice_duration
        output_path = os.path.join(output_dir, f"slice_{i:03d}.mp4")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-ss", str(start_time),
            "-t", str(slice_duration),
            "-c:v", "libx264", "-c:a", "aac",
            "-movflags", "+faststart",
            output_path,
        ]
        logger.info(f"切片 {i + 1}/{num_slices}: {start_time}s - {start_time + slice_duration}s")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"视频切片失败 (slice {i}): {result.stderr}")
        slice_paths.append(output_path)

    logger.info(f"视频切片完成，共 {len(slice_paths)} 个片段")
    return slice_paths


def concat_videos(video_paths: list[str], output_path: str) -> str:
    """将多个视频片段拼接成最终视频，返回输出路径。"""
    if not video_paths:
        raise ValueError("没有视频文件可拼接")
    if len(video_paths) == 1:
        return video_paths[0]

    valid_paths = [p for p in video_paths if os.path.exists(p) and os.path.getsize(p) > 0]
    if not valid_paths:
        raise ValueError("没有有效的视频文件可拼接")
    if len(valid_paths) == 1:
        return valid_paths[0]

    list_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="adsflow_concat_"
    )
    try:
        for path in valid_paths:
            list_file.write(f"file '{os.path.abspath(path)}'\n")
        list_file.close()

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_file.name,
            "-c", "copy",
            output_path,
        ]
        logger.info(f"开始拼接 {len(valid_paths)} 个视频片段...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.warning(f"copy 模式拼接失败，尝试重新编码: {result.stderr[:200]}")
            cmd_reencode = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", list_file.name,
                "-c:v", "libx264", "-c:a", "aac",
                output_path,
            ]
            result = subprocess.run(cmd_reencode, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"视频拼接失败: {result.stderr}")

        file_size = os.path.getsize(output_path) / (1024 * 1024)
        logger.info(f"视频拼接完成: {output_path} ({file_size:.2f} MB)")
        return output_path
    finally:
        os.unlink(list_file.name)


def extract_audio(video_path: str, output_path: str) -> str:
    """从视频中提取音频轨道。"""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn", "-acodec", "aac",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"音频提取失败: {result.stderr}")
    logger.info(f"音频提取完成: {output_path}")
    return output_path


def add_audio_to_video(video_path: str, audio_path: str, output_path: str) -> str:
    """将音频添加到视频中（替换或叠加）。"""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy", "-c:a", "aac",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"音频添加失败: {result.stderr}")
    logger.info(f"音频添加完成: {output_path}")
    return output_path


def trim_video(video_path: str, start: float, duration: float, output_path: str) -> str:
    """截取视频的指定片段。"""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-ss", str(start),
        "-t", str(duration),
        "-c:v", "libx264", "-c:a", "aac",
        "-movflags", "+faststart",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"视频截取失败: {result.stderr}")
    logger.info(f"视频截取完成: {output_path}")
    return output_path
