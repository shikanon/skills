import json
import os

from ui_tester.vlm_client import VLMClient
from ui_tester.config import REPORTS_DIR
from ui_tester.logger import logger


COMPARISON_PROMPT = """你是一位资深的 UI/UX 质量保证工程师。请将以下网页视觉分析结果与 UI 需求文档进行对比，找出所有差异。

**网页视觉分析结果**：
{analysis}

**UI 需求文档**：
{requirement}

请从以下 8 个维度进行对比，并按严重程度排序：

1. **布局差异**：实际布局 vs 需求布局
2. **色彩差异**：实际色彩 vs 需求色彩
3. **字体差异**：实际字体 vs 需求字体
4. **组件差异**：实际组件样式 vs 需求组件样式
5. **缺失元素**：需求中有但页面中没有的元素
6. **多余元素**：页面中有但需求中没有的元素
7. **用户体验差异**：信息架构、操作流程、关键信息突出度、用户引导、认知负担等方面与需求的差异
8. **视觉美观性差异**：整体协调性、留白节奏、图文搭配、品牌调性、视觉杂乱度等方面与需求的差异

请以 JSON 格式输出：
{
  "differences": [
    {
      "category": "layout/color/typography/component/missing/extra/ux/aesthetics",
      "severity": "critical/major/minor/suggestion",
      "description": "差异描述",
      "expected": "需求期望",
      "actual": "实际表现",
      "fix_suggestion": "修复建议（包含具体的 CSS/HTML/交互逻辑修改建议）"
    }
  ],
  "summary": {
    "critical_count": 0,
    "major_count": 0,
    "minor_count": 0,
    "suggestion_count": 0,
    "overall_match_score": 85.0
  },
  "optimization_suggestions": [
    {
      "category": "ux/accessibility/performance/visual",
      "description": "优化建议描述",
      "priority": "high/medium/low",
      "implementation": "具体实现建议"
    }
  ]
}"""


def compare_with_requirement(
    analysis_path: str,
    requirement_path: str,
    output_path: str | None = None,
    vlm_backend: str = "volcengine",
) -> dict:
    """将视觉分析结果与 UI 需求文档对比，返回差异字典。"""
    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis = json.load(f)

    if not os.path.isfile(requirement_path):
        raise FileNotFoundError(f"UI 需求文档不存在: {requirement_path}")
    with open(requirement_path, "r", encoding="utf-8") as f:
        requirement = f.read()

    prompt = COMPARISON_PROMPT.format(
        analysis=json.dumps(analysis, ensure_ascii=False, indent=2)[:3000],
        requirement=requirement[:3000],
    )

    client = VLMClient(backend=vlm_backend)
    response = client.chat([{"role": "user", "content": prompt}])

    try:
        text = response
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        comparison = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("对比结果非标准 JSON，使用原始文本")
        comparison = {"raw_comparison": response}

    comparison["analysis_path"] = analysis_path
    comparison["requirement_path"] = requirement_path

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(comparison, f, ensure_ascii=False, indent=2)
        logger.info(f"对比结果已保存: {output_path}")

    return comparison
