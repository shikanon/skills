# ── Step 1: VLM 识别替换图片 ──

IMAGE_IDENTIFY_PROMPT = """请分析这张图片，判断图片中是否包含真人面部。

判断标准：
- 如果图片中有清晰可辨的真人面部/人像，判定为真人图片
- 如果图片是产品、风景、卡通、AI生成人像等，判定为非真人图片

请以 JSON 格式输出：
{
  "is_real_person": true/false,
  "description": "图片内容简要描述",
  "person_count": 0,
  "suggested_action": "use_directly（直接使用） 或 regenerate_via_seedream（需通过Seedream重新生成）"
}"""

# ── Step 1 补充: Seedream 图生图提示词 ──

SEEDREAM_REGENERATE_PROMPT = """基于原始图片的风格和构图，生成一张相似风格的图片。

原始图片描述：{image_description}
替换要求：{replace_requirement}

要求：
1. 保持与原始图片相似的视觉风格和构图
2. 不包含任何真实人物面部
3. 符合广告视频的视觉品质要求"""

# ── Step 2: Seedance 视频生成提示词 ──

SEEDANCE_REPLACE_PROMPT = """你是一位专业的 Seedance 视频提示词工程师。

请根据以下信息，为 Seedance 2.0 编写精准的视频生成提示词：

**参考视频**：视频1（原广告视频片段，时长 {duration} 秒）
**参考图片**：图片1（替换用的产品/元素图片）
**替换要求**：{replace_requirement}

提示词要求：
1. 参考视频1的运镜方式和整体风格，保持一致
2. 将图片1中的产品/元素融入视频，替换原视频中的对应元素
3. 保持视频1的节奏和叙事结构
4. 详细描述每一帧的视觉内容
5. 使用英文编写提示词

请以 JSON 格式输出：
{{
  "prompt": "完整的英文视频生成提示词",
  "style_notes": "风格说明",
  "key_changes": ["主要替换点1", "主要替换点2"]
}}"""

# ── Step 3: 视频对比检查 ──

VIDEO_COMPARE_PROMPT = """请对比以下两个视频：

- 视频1：原始广告视频片段
- 视频2：替换后的广告视频片段

请从以下维度评估替换效果：

1. **替换完整性**：目标产品/元素是否成功替换
2. **风格一致性**：替换后的视频是否与原视频风格一致
3. **视觉连贯性**：画面过渡是否自然流畅
4. **运镜一致性**：镜头运动是否与原视频保持一致
5. **整体质量**：视频的整体视觉质量

请以 JSON 格式输出：
{
  "replacement_completeness": 8,
  "style_consistency": 7,
  "visual_continuity": 8,
  "camera_consistency": 9,
  "overall_quality": 8,
  "overall_score": 8.0,
  "issues": ["问题1"],
  "passed": true,
  "improved_prompt": "如果未通过，提供改进后的提示词"
}

通过标准：overall_score >= 7.0。"""
