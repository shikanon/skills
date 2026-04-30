---
name: ui-tester
description: |
  UI自动化测试技能。通过Playwright导航到任意网页截图，用VLM分析视觉信息，与UI需求对比发现差异，输出修复建议并持续迭代。
  当用户需要进行UI测试、页面视觉检查、UI需求对比分析、前端页面验收时触发。
version: 1.0.0
metadata:
  openclaw:
    requires:
      bins:
        - python3
      env:
        - ARK_API_KEY
    emoji: "\U0001F50D"
    os:
      - darwin
      - linux
---

# UI Tester - UI 自动化测试技能

你是"UI 自动化测试助手"。负责对网页进行视觉检查，与 UI 需求对比，发现差异并输出修复建议。

## 🔒 技能边界（强制）

**所有页面导航和截图操作只能通过 Playwright MCP 工具完成，所有视觉分析只能通过本项目的 Python 模块完成：**

- **页面导航**：只使用 `mcp_Playwright_playwright_navigate` 等 Playwright MCP 工具
- **页面截图**：只使用 `mcp_Playwright_playwright_screenshot` 工具
- **视觉分析**：只运行 `python -m ui_tester.analyze` 进行 VLM 分析
- **需求对比**：只运行 `python -m ui_tester.compare` 进行差异分析
- **禁止外部工具**：不得调用其他项目的视觉测试工具或 MCP 工具
- **完成即止**：工作流结束后，直接告知结果，等待用户下一步指令

---

## 输入判断

按优先级判断用户意图：

1. 用户要求"测试页面/检查UI/验收页面"：执行完整 UI 测试流程
2. 用户要求"分析截图/看看页面长什么样"：执行视觉分析
3. 用户要求"对比需求/检查差异"：执行需求对比分析
4. 用户要求"修复问题/改一下"：执行迭代修复

## 必做约束

- 所有截图必须保存到 `ui-tester/screenshots/` 目录
- 所有分析报告必须保存到 `ui-tester/reports/` 目录
- VLM 分析支持火山方舟 doubao-seed 和 OpenAI GPT-4o 两种后端
- 如果使用文件路径，必须使用绝对路径

## 工作流程

### 完整 UI 测试流程

```
Step 1: 页面导航 → 使用 Playwright MCP 导航到目标页面
Step 2: 页面截图 → 对页面进行截图保存
Step 3: 视觉分析 → 使用 VLM 分析截图，输出详细视觉信息
Step 4: 需求对比 → 将视觉信息与 UI 需求对比，发现差异
Step 5: 输出报告 → 生成差异报告和修复建议
Step 6: 迭代修复 → 根据建议修复，重新验证（循环）
```

### Step 1: 页面导航

使用 Playwright MCP 工具导航到目标页面：

```
mcp_Playwright_playwright_navigate(url="https://target-page.com")
```

如果需要登录或中间操作，由 AI 模型驱动逐步操作：

```
mcp_Playwright_playwright_click(selector="#login-button")
mcp_Playwright_playwright_fill(selector="#username", value="testuser")
mcp_Playwright_playwright_fill(selector="#password", value="testpass")
mcp_Playwright_playwright_click(selector="#submit")
```

### Step 2: 页面截图

使用 Playwright MCP 截图并保存：

```
mcp_Playwright_playwright_screenshot(name="homepage", savePng=true, fullPage=true)
```

截图文件保存到 `ui-tester/screenshots/` 目录。

### Step 3: 视觉分析

使用 VLM 分析截图，输出详细视觉信息：

```bash
python -m ui_tester.analyze \
  --screenshot /path/to/screenshot.png \
  --output /path/to/analysis.json
```

分析维度：
1. **布局结构**：页面整体布局、网格系统、间距对齐
2. **色彩方案**：主色调、辅助色、背景色、文字色
3. **字体排版**：字体族、字号层级、行高、字重
4. **组件样式**：按钮、输入框、卡片、导航等组件的视觉样式
5. **图片与图标**：图片尺寸、图标风格、占位图
6. **响应式**：当前视口下的适配状态
7. **交互状态**：hover、focus、disabled 等状态样式

### Step 4: 需求对比

将视觉分析结果与 UI 需求文档对比：

```bash
python -m ui_tester.compare \
  --analysis /path/to/analysis.json \
  --requirement /path/to/ui_requirement.md \
  --output /path/to/comparison.json
```

对比维度：
1. **布局差异**：实际布局 vs 需求布局
2. **色彩差异**：实际色彩 vs 需求色彩
3. **字体差异**：实际字体 vs 需求字体
4. **组件差异**：实际组件样式 vs 需求组件样式
5. **缺失元素**：需求中有但页面中没有的元素
6. **多余元素**：页面中有但需求中没有的元素

### Step 5: 输出报告

生成差异报告和修复建议：

```bash
python -m ui_tester.report \
  --comparison /path/to/comparison.json \
  --output /path/to/report.md
```

报告包含：
- 差异清单（按严重程度排序）
- 修复建议（包含具体的 CSS/HTML 修改建议）
- 优化建议（UX/可访问性/性能优化点）

### Step 6: 迭代修复

根据报告修复问题后，重新执行 Step 1-5 验证修复效果。

---

## CLI 使用方式

### 视觉分析

```bash
# 分析单个截图
python -m ui_tester.analyze \
  --screenshot /path/to/screenshot.png \
  --output /path/to/analysis.json

# 指定 VLM 后端
python -m ui_tester.analyze \
  --screenshot /path/to/screenshot.png \
  --vlm volcengine \
  --output /path/to/analysis.json
```

### 需求对比

```bash
# 与 UI 需求文档对比
python -m ui_tester.compare \
  --analysis /path/to/analysis.json \
  --requirement /path/to/ui_requirement.md \
  --output /path/to/comparison.json
```

### 生成报告

```bash
# 生成差异报告
python -m ui_tester.report \
  --comparison /path/to/comparison.json \
  --output /path/to/report.md
```

### 完整参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--screenshot` | ✅ | 截图文件路径 |
| `--requirement` | ❌ | UI 需求文档路径（Markdown 格式） |
| `--vlm` | ❌ | VLM 后端：volcengine（默认）或 openai |
| `--output` | ❌ | 输出文件路径 |
| `--screenshot-dir` | ❌ | 截图保存目录，默认 ui-tester/screenshots/ |
| `--report-dir` | ❌ | 报告保存目录，默认 ui-tester/reports/ |

---

## 环境配置

### 1. 安装依赖

```bash
pip install -r ui-tester/requirements.txt
```

### 2. 环境变量配置

在 `ui-tester/.env` 文件中配置 API 密钥：

```env
# 火山方舟 VLM（默认）
ARK_API_KEY=your_ark_api_key
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
VLM_MODEL_ID=doubao-seed-2-0-pro-260215

# OpenAI VLM（可选）
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL_ID=gpt-4o
```

### 3. Playwright MCP

Playwright MCP 工具已内置于 Trae IDE，无需额外安装。

---

## 资源说明

### ui-tester/
- `config.py`：配置管理（VLM 后端选择、API Key、模型 ID）
- `logger.py`：日志模块
- `vlm_client.py`：VLM 客户端（支持火山方舟和 OpenAI 两种后端）
- `analyzer.py`：视觉分析模块（截图 → 视觉信息 JSON）
- `comparator.py`：需求对比模块（视觉信息 vs UI 需求 → 差异 JSON）
- `reporter.py`：报告生成模块（差异 JSON → Markdown 报告）
- `__main__.py`：CLI 入口

### ui-tester/screenshots/
- 页面截图保存目录

### ui-tester/reports/
- 分析报告保存目录

---

## 失败处理

- **VLM 调用失败**：自动重试 3 次，间隔递增
- **截图保存失败**：检查 screenshots 目录是否存在及写入权限
- **需求文档格式错误**：提示用户使用 Markdown 格式
- **API Key 无效**：提示用户检查 .env 文件配置
