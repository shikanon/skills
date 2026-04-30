#!/usr/bin/env python3
"""UI Tester - UI 自动化测试 CLI 入口。

用法示例：
  # 分析截图
  python ui-tester/__main__.py analyze --screenshot /path/to/screenshot.png

  # 需求对比
  python ui-tester/__main__.py compare --analysis /path/to/analysis.json --requirement /path/to/ui.md

  # 生成报告
  python ui-tester/__main__.py report --comparison /path/to/comparison.json
"""

import argparse
import json
import os
import sys

# 将 ui-tester 目录加入 sys.path，使模块可以直接 import
_ui_tester_dir = os.path.dirname(os.path.abspath(__file__))
_skills_dir = os.path.dirname(_ui_tester_dir)
if _skills_dir not in sys.path:
    sys.path.insert(0, _skills_dir)

# 将 ui-tester 目录本身也加入，支持直接运行
if _ui_tester_dir not in sys.path:
    sys.path.insert(0, _ui_tester_dir)

# 重命名模块路径：ui-tester 目录 -> ui_tester 包
import importlib
import types

# 创建 ui_tester 包模块并注册
_ui_tester_pkg = types.ModuleType("ui_tester")
_ui_tester_pkg.__path__ = [_ui_tester_dir]
_ui_tester_pkg.__package__ = "ui_tester"
sys.modules["ui_tester"] = _ui_tester_pkg

from ui_tester.config import SCREENSHOTS_DIR, REPORTS_DIR, DEFAULT_VLM_BACKEND
from ui_tester.logger import logger


def cmd_analyze(args):
    from ui_tester.analyzer import analyze_screenshot

    output = args.output or os.path.join(REPORTS_DIR, "analysis.json")
    os.makedirs(REPORTS_DIR, exist_ok=True)

    result = analyze_screenshot(
        screenshot_path=args.screenshot,
        output_path=output,
        vlm_backend=args.vlm,
    )
    print(f"\n✅ 视觉分析完成！结果已保存: {output}")
    summary = result.get("overall_impression", "N/A")
    print(f"📋 整体印象: {summary}")
    return result


def cmd_compare(args):
    from ui_tester.comparator import compare_with_requirement

    output = args.output or os.path.join(REPORTS_DIR, "comparison.json")
    os.makedirs(REPORTS_DIR, exist_ok=True)

    result = compare_with_requirement(
        analysis_path=args.analysis,
        requirement_path=args.requirement,
        output_path=output,
        vlm_backend=args.vlm,
    )
    summary = result.get("summary", {})
    score = summary.get("overall_match_score", "N/A")
    critical = summary.get("critical_count", 0)
    major = summary.get("major_count", 0)
    print(f"\n✅ 需求对比完成！结果已保存: {output}")
    print(f"📊 匹配度: {score}%，严重问题: {critical}，主要问题: {major}")
    return result


def cmd_report(args):
    from ui_tester.reporter import generate_report

    output = args.output or os.path.join(REPORTS_DIR, "report.md")
    os.makedirs(REPORTS_DIR, exist_ok=True)

    report = generate_report(
        comparison_path=args.comparison,
        output_path=output,
    )
    print(f"\n✅ 差异报告已生成: {output}")
    return report


def main():
    parser = argparse.ArgumentParser(description="UI Tester - UI 自动化测试工具")
    subparsers = parser.add_subparsers(dest="command", help="选择操作")

    # ── 视觉分析 ──
    analyze_parser = subparsers.add_parser("analyze", help="分析截图的视觉信息")
    analyze_parser.add_argument("--screenshot", required=True, help="截图文件路径")
    analyze_parser.add_argument("--vlm", default=DEFAULT_VLM_BACKEND, choices=["volcengine", "openai"], help="VLM 后端")
    analyze_parser.add_argument("--output", default=None, help="输出文件路径")
    analyze_parser.set_defaults(func=cmd_analyze)

    # ── 需求对比 ──
    compare_parser = subparsers.add_parser("compare", help="将视觉分析与 UI 需求对比")
    compare_parser.add_argument("--analysis", required=True, help="视觉分析 JSON 文件路径")
    compare_parser.add_argument("--requirement", required=True, help="UI 需求文档路径（Markdown）")
    compare_parser.add_argument("--vlm", default=DEFAULT_VLM_BACKEND, choices=["volcengine", "openai"], help="VLM 后端")
    compare_parser.add_argument("--output", default=None, help="输出文件路径")
    compare_parser.set_defaults(func=cmd_compare)

    # ── 生成报告 ──
    report_parser = subparsers.add_parser("report", help="生成差异报告")
    report_parser.add_argument("--comparison", required=True, help="对比结果 JSON 文件路径")
    report_parser.add_argument("--output", default=None, help="输出文件路径（Markdown）")
    report_parser.set_defaults(func=cmd_report)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
