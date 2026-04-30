import json
import os
from datetime import datetime

from ui_tester.logger import logger


_SEVERITY_EMOJI = {
    "critical": "🔴",
    "major": "🟠",
    "minor": "🟡",
    "suggestion": "🟢",
}

_PRIORITY_EMOJI = {
    "high": "🔴",
    "medium": "🟠",
    "low": "🟢",
}


def generate_report(
    comparison_path: str,
    output_path: str | None = None,
) -> str:
    """从对比结果生成 Markdown 格式的差异报告。"""
    with open(comparison_path, "r", encoding="utf-8") as f:
        comparison = json.load(f)

    lines = []
    lines.append("# UI 测试差异报告\n")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 摘要
    summary = comparison.get("summary", {})
    lines.append("## 📊 摘要\n")
    lines.append(f"| 严重程度 | 数量 |")
    lines.append(f"|----------|------|")
    lines.append(f"| 🔴 严重 | {summary.get('critical_count', 0)} |")
    lines.append(f"| 🟠 主要 | {summary.get('major_count', 0)} |")
    lines.append(f"| 🟡 次要 | {summary.get('minor_count', 0)} |")
    lines.append(f"| 🟢 建议 | {summary.get('suggestion_count', 0)} |")
    lines.append(f"\n**整体匹配度**: {summary.get('overall_match_score', 'N/A')}%\n")

    # 差异详情
    differences = comparison.get("differences", [])
    if differences:
        lines.append("## 🔍 差异详情\n")
        for i, diff in enumerate(differences, 1):
            severity = diff.get("severity", "minor")
            emoji = _SEVERITY_EMOJI.get(severity, "⚪")
            category = diff.get("category", "unknown")
            lines.append(f"### {emoji} 差异 {i}: [{category}] {diff.get('description', '')}\n")
            lines.append(f"- **严重程度**: {severity}")
            lines.append(f"- **期望**: {diff.get('expected', 'N/A')}")
            lines.append(f"- **实际**: {diff.get('actual', 'N/A')}")
            lines.append(f"- **修复建议**: {diff.get('fix_suggestion', 'N/A')}")
            lines.append("")

    # 优化建议
    optimizations = comparison.get("optimization_suggestions", [])
    if optimizations:
        lines.append("## 💡 优化建议\n")
        for i, opt in enumerate(optimizations, 1):
            priority = opt.get("priority", "low")
            emoji = _PRIORITY_EMOJI.get(priority, "⚪")
            category = opt.get("category", "general")
            lines.append(f"### {emoji} 优化 {i}: [{category}] {opt.get('description', '')}\n")
            lines.append(f"- **优先级**: {priority}")
            lines.append(f"- **实现建议**: {opt.get('implementation', 'N/A')}")
            lines.append("")

    report = "\n".join(lines)

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"差异报告已保存: {output_path}")

    return report
