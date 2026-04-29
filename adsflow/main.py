#!/usr/bin/env python3
"""AdsFlow 广告工作流引擎 - CLI 入口。

支持两种工作流：
1. replace  - 爆款裂变工作流：将长广告视频中的产品/元素替换为用户指定内容
2. prelude  - 广告前贴工作流：为原广告视频生成一个吸引人的前贴片段

用法示例：
  # 爆款裂变工作流
  python main.py replace \\
    --video https://example.com/original_ad.mp4 \\
    --replace-images https://example.com/product1.jpg https://example.com/product2.jpg \\
    --requirement "将视频中的香水替换为面霜，运镜不变"

  # 广告前贴工作流
  python main.py prelude \\
    --video ./original_ad.mp4 \\
    --duration 10
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adsflow.seedance_client import SeedanceClient
from adsflow.replace_flow import ReplaceFlow, ReplaceFlowConfig
from adsflow.prelude_flow import PreludeFlow, PreludeFlowConfig
from adsflow.config import OUTPUT_DIR
from adsflow.logger import logger


def cmd_replace(args):
    """执行爆款裂变工作流。"""
    client = SeedanceClient()

    config = ReplaceFlowConfig(
        video_path=args.video,
        replace_images=args.replace_images or [],
        replace_requirement=args.requirement,
        slice_duration=args.slice_duration,
        ratio=args.ratio,
        resolution=args.resolution,
        generate_audio=not args.no_audio,
        watermark=args.watermark,
        compare_check_enabled=not args.skip_compare,
        compare_pass_threshold=args.compare_threshold,
        max_compare_retries=args.compare_retries,
        output_dir=args.output_dir,
    )

    flow = ReplaceFlow(client, config)
    result = flow.run()
    print(f"\n✅ 爆款裂变工作流完成！最终视频: {result}")
    return result


def cmd_prelude(args):
    """执行广告前贴工作流。"""
    client = SeedanceClient()

    config = PreludeFlowConfig(
        video_path=args.video,
        prelude_duration=args.duration,
        ratio=args.ratio,
        resolution=args.resolution,
        generate_audio=not args.no_audio,
        watermark=args.watermark,
        output_dir=args.output_dir,
    )

    flow = PreludeFlow(client, config)
    result = flow.run()
    print(f"\n✅ 广告前贴工作流完成！最终视频: {result}")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="AdsFlow 广告工作流引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", help="选择工作流类型")

    # ── 爆款裂变工作流 ──
    replace_parser = subparsers.add_parser("replace", help="爆款裂变工作流")
    replace_parser.add_argument("--video", required=True, help="原始视频路径或 URL")
    replace_parser.add_argument(
        "--replace-images", nargs="+", default=[],
        help="替换图片 URL 列表（如为真人图片会自动用 Seedream 5.0 重新生成）",
    )
    replace_parser.add_argument(
        "--requirement", required=True,
        help="替换要求描述（如：将视频中的香水替换为面霜，运镜不变）",
    )
    replace_parser.add_argument("--slice-duration", type=int, default=15, help="视频切片时长（秒）")
    replace_parser.add_argument("--ratio", default="16:9", help="视频宽高比")
    replace_parser.add_argument("--resolution", default="720p", help="视频分辨率")
    replace_parser.add_argument("--no-audio", action="store_true", help="不生成音频")
    replace_parser.add_argument("--watermark", action="store_true", help="添加水印")
    replace_parser.add_argument("--skip-compare", action="store_true", help="跳过视频对比检查")
    replace_parser.add_argument("--compare-threshold", type=float, default=7.0, help="对比检查通过阈值")
    replace_parser.add_argument("--compare-retries", type=int, default=2, help="对比检查最大重试次数")
    replace_parser.add_argument("--output-dir", default=OUTPUT_DIR, help="输出目录")
    replace_parser.set_defaults(func=cmd_replace)

    # ── 广告前贴工作流 ──
    prelude_parser = subparsers.add_parser("prelude", help="广告前贴工作流")
    prelude_parser.add_argument("--video", required=True, help="原始视频路径或 URL")
    prelude_parser.add_argument("--duration", type=int, default=10, help="前贴时长（秒，最大15秒）")
    prelude_parser.add_argument("--ratio", default="16:9", help="视频宽高比")
    prelude_parser.add_argument("--resolution", default="720p", help="视频分辨率")
    prelude_parser.add_argument("--no-audio", action="store_true", help="不生成音频")
    prelude_parser.add_argument("--watermark", action="store_true", help="添加水印")
    prelude_parser.add_argument("--output-dir", default=OUTPUT_DIR, help="输出目录")
    prelude_parser.set_defaults(func=cmd_prelude)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
