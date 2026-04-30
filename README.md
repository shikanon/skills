# 最佳Skills实践仓库

本仓库沉淀了OpenClaw平台下经过实战验证的优质技能，可直接导入使用。

## 已收录技能列表

| 技能名称 | 功能说明 |
|---------|---------|
| xiaohongshu-hot-content-generator | 自动生成小红书热门图文内容，支持搜索案例、生成4K图片、质量校验、飞书自动发送 |
| ai-movie-generator | AI 电影生成器，支持剧本分析、角色设计、分镜生成、视频拼接全流程，5个Agent协作 |
| adsflow | 广告爆款裂变工作流，输入长广告视频+替换图片+替换要求，自动完成视频切片、VLM图片识别、Seedance 2.0视频生成、视频对比检查、视频拼接 |
| ui-tester | UI自动化测试技能，通过Playwright导航截图，VLM分析视觉信息，与UI需求对比发现差异，输出修复建议并持续迭代 |
| 更多技能持续更新中... | |

---

## AdsFlow 广告爆款裂变工作流

🎬 基于 Seedance 2.0 + Seedream 5.0 + VLM 的广告视频爆款裂变技能。

### 核心能力

输入长广告视频、替换图片和替换要求，自动完成以下 5 步流程：

```
Step 0: 视频切片检查 → 超过15秒自动切片，记录每个切片时长（四舍五入取整）
Step 1: VLM 识别替换图片 → 真人图片自动用 Seedream 5.0 图生图重新生成
Step 2: Seedance 视频生成 → 输入参考视频（切片）+ 参考图 + 替换要求 + 视频时长
Step 3: 视频对比检查 → VLM 对比原视频和替换后视频，评估5个维度，不合格自动重试
Step 4: 视频拼接 → 多片段合并为最终视频
```

### 技术栈

| 组件 | 模型/工具 | 用途 |
|------|----------|------|
| 视频生成 | Seedance 2.0 (`doubao-seedance-2-0-260128`) | 多模态参考视频生成、视频编辑 |
| 图片生成 | Seedream 5.0 (`doubao-seedream-5-0-260128`) | 真人图片合规化图生图 |
| 视觉理解 | VLM (`doubao-seed-2-0-pro-260215`) | 图片识别、视频对比检查 |
| 视频处理 | FFmpeg | 切片、拼接、音频提取/合成 |

### 使用方式

```bash
# 爆款裂变工作流
python -m adsflow.main replace \
  --video https://example.com/ad.mp4 \
  --replace-images https://example.com/product.jpg \
  --requirement "将视频中的香水替换为面霜，运镜不变"

# 广告前贴工作流
python -m adsflow.main prelude \
  --video /path/to/ad.mp4 \
  --duration 10
```

### 环境配置

1. **安装依赖**：`pip install -r adsflow/requirements.txt`
2. **系统依赖**：`brew install ffmpeg`（macOS）
3. **配置环境变量**：复制 `adsflow/.env.example` 为 `adsflow/.env`，填入 `ARK_API_KEY`

---

## UI Tester UI 自动化测试

🔍 基于 Playwright MCP + VLM 的 UI 自动化测试技能。

### 核心能力

通过 Playwright 导航到任意网页截图，用 VLM 分析视觉信息，与 UI 需求对比发现差异，输出修复建议并持续迭代：

```
Step 1: 页面导航 → 使用 Playwright MCP 导航到目标页面（AI模型驱动中间操作）
Step 2: 页面截图 → 对页面进行截图保存
Step 3: 视觉分析 → 使用 VLM 分析截图，输出7维度详细视觉信息
Step 4: 需求对比 → 将视觉信息与 UI 需求对比，发现差异
Step 5: 输出报告 → 生成差异报告和修复建议（含CSS/HTML修改建议）
Step 6: 迭代修复 → 根据建议修复，重新验证（循环）
```

### 技术栈

| 组件 | 模型/工具 | 用途 |
|------|----------|------|
| 页面导航 | Playwright MCP | 导航、交互、截图 |
| 视觉分析 | VLM (doubao-seed / GPT-4o) | 7维度视觉信息提取 |
| 需求对比 | VLM | 差异发现和严重程度分级 |
| 报告生成 | Python | Markdown 格式差异报告 |

### 使用方式

```bash
# 分析截图
python ui-tester/__main__.py analyze \
  --screenshot /path/to/screenshot.png \
  --vlm volcengine

# 需求对比
python ui-tester/__main__.py compare \
  --analysis /path/to/analysis.json \
  --requirement /path/to/ui_requirement.md

# 生成报告
python ui-tester/__main__.py report \
  --comparison /path/to/comparison.json
```

### 环境配置

1. **安装依赖**：`pip install -r ui-tester/requirements.txt`
2. **配置环境变量**：复制 `ui-tester/.env.example` 为 `ui-tester/.env`，填入 `ARK_API_KEY` 或 `OPENAI_API_KEY`
3. **Playwright MCP**：已内置于 Trae IDE，无需额外安装

---

## 使用说明
1. 下载对应的`.skill`技能包
2. 在OpenClaw平台导入技能包即可使用
3. 所有技能均已移除硬编码密钥，使用前请配置对应的环境变量

## 环境变量配置
使用技能前请配置以下环境变量：
- `ARK_API_KEY`: 火山引擎Ark大模型API密钥
- `OPENAI_API_KEY`: OpenAI API密钥（可选，UI测试技能需要）
- `MODEL_VIDEO_NAME`: 视频生成模型ID（可选，视频类技能需要）
- `VOLCENGINE_ACCESS_KEY`: 火山引擎Access Key（可选，部分服务需要）
- `VOLCENGINE_SECRET_KEY`: 火山引擎Secret Key（可选，部分服务需要）
