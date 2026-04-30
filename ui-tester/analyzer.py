import json
import os

from ui_tester.vlm_client import VLMClient
from ui_tester.config import SCREENSHOTS_DIR, REPORTS_DIR
from ui_tester.logger import logger


ANALYSIS_PROMPT = """你是一位专业的 UI/UX 设计分析师。请对以下网页截图进行详细的视觉分析。

请从以下 7 个维度进行深入分析：

1. **布局结构**：页面整体布局方式（网格/Flex/自由布局）、主要区域划分、间距对齐方式
2. **色彩方案**：主色调、辅助色、背景色、文字色、品牌色，标注具体颜色值（如可识别）
3. **字体排版**：字体族、字号层级（H1-H6/正文/辅助文字）、行高、字重
4. **组件样式**：按钮（形状/圆角/阴影/颜色）、输入框、卡片、导航栏、标签页等组件的视觉样式
5. **图片与图标**：图片尺寸比例、图标风格（线性/填充/圆角）、占位图情况
6. **响应式状态**：当前视口下的适配状态、是否存在溢出或截断
7. **交互状态**：可识别的 hover/focus/active/disabled 等状态样式

请以 JSON 格式输出：
{
  "layout": {
    "type": "grid/flex/free",
    "sections": ["header", "nav", "main", "sidebar", "footer"],
    "alignment": "描述对齐方式",
    "spacing": "描述间距规律"
  },
  "colors": {
    "primary": "#hex",
    "secondary": "#hex",
    "background": "#hex",
    "text_primary": "#hex",
    "text_secondary": "#hex",
    "accent": "#hex"
  },
  "typography": {
    "font_family": "描述字体族",
    "heading_sizes": ["H1: 大约Xpx", "H2: 大约Xpx"],
    "body_size": "大约Xpx",
    "line_height": "描述行高",
    "font_weights": ["描述字重层级"]
  },
  "components": [
    {
      "type": "button/input/card/nav/tab",
      "description": "详细描述组件样式",
      "border_radius": "描述圆角",
      "shadow": "描述阴影",
      "colors": "描述颜色"
    }
  ],
  "images_and_icons": {
    "image_style": "描述图片风格",
    "icon_style": "描述图标风格",
    "count": "图片和图标数量估计"
  },
  "responsive": {
    "viewport": "当前视口描述",
    "adaptation": "适配状态描述",
    "issues": ["溢出/截断等问题"]
  },
  "interaction_states": {
    "observed_states": ["hover/focus/active/disabled等"],
    "description": "描述交互状态样式"
  },
  "overall_impression": "整体视觉印象一句话总结",
  "accessibility_notes": ["可访问性相关观察"]
}"""


def analyze_screenshot(
    screenshot_path: str,
    output_path: str | None = None,
    vlm_backend: str = "volcengine",
) -> dict:
    """分析截图，返回视觉信息字典。"""
    if not os.path.isfile(screenshot_path):
        raise FileNotFoundError(f"截图文件不存在: {screenshot_path}")

    client = VLMClient(backend=vlm_backend)
    response = client.analyze_image(screenshot_path, ANALYSIS_PROMPT)

    try:
        text = response
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        analysis = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("VLM 分析结果非标准 JSON，使用原始文本")
        analysis = {"raw_analysis": response}

    analysis["screenshot_path"] = screenshot_path
    analysis["vlm_backend"] = vlm_backend

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        logger.info(f"分析结果已保存: {output_path}")

    return analysis
