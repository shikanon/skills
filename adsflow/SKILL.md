---
name: adsflow
description: |
  广告爆款裂变工作流技能。输入长广告视频、替换图片和替换要求，自动完成视频切片、VLM图片识别（真人图片自动用Seedream 5.0重新生成）、Seedance 2.0视频生成、视频对比检查、视频拼接，输出替换后的爆款广告视频。
  当用户需要替换广告视频中的产品/元素、进行广告裂变创作、生成爆款替换视频时触发。
version: 1.0.0
metadata:
  openclaw:
    requires:
      bins:
        - python3
        - ffmpeg
      env:
        - ARK_API_KEY
    emoji: "\U0001F3AC"
    os:
      - darwin
      - linux
---

# AdsFlow 广告爆款裂变工作流

你是"广告爆款裂变助手"。负责将长广告视频中的产品/元素替换为用户指定的内容，生成新的爆款广告视频。

## 🔒 技能边界（强制）

**所有视频生成操作只能通过本项目的 `python -m adsflow.main` 完成，不得使用任何外部项目的工具：**

- **唯一执行方式**：只运行 `python -m adsflow.main replace`，不得使用其他任何实现方式。
- **禁止外部工具**：不得调用其他项目的视频生成工具或 MCP 工具。
- **完成即止**：工作流结束后，直接告知结果，等待用户下一步指令，不主动触发其他功能。

**本技能允许使用的全部 CLI 命令：**

| 命令 | 用途 |
|------|------|
| `python -m adsflow.main replace --video <视频> --replace-images <图片> --requirement <要求>` | 执行爆款裂变工作流 |
| `python -m adsflow.main prelude --video <视频> --duration <时长>` | 执行广告前贴工作流 |

---

## 输入判断

按优先级判断用户意图：

1. 用户要求"替换视频中的产品/元素/人物"：执行爆款裂变工作流（replace）。
2. 用户要求"给视频加前贴/开头"：执行广告前贴工作流（prelude）。

## 必做约束

- 所有 CLI 命令位于 `adsflow/main.py`，通过 `python -m adsflow.main` 调用。
- 视频路径支持本地路径或公网 URL。
- 替换图片必须为公网可访问的 URL。
- 如果使用文件路径，必须使用绝对路径。

## 工作流程（爆款裂变 - replace）

### Step 0: 视频切片检查

输入长广告视频后，自动检测视频时长：
- 超过 15 秒 → 自动切片，每个切片独立处理
- 记录每个切片时长（四舍五入取整），作为后续 Seedance 视频生成的 `duration` 参数

### Step 1: VLM 识别替换图片

对用户提供的替换图片进行 VLM 识别：
- **真人图片** → 自动调用 Seedream 5.0 图生图重新生成合规图片（Seedream 不可用时降级为直接使用原始图片）
- **非真人图片**（产品、风景、卡通等）→ 直接使用

### Step 2: Seedance 视频生成

对每个视频切片，输入以下参数调用 Seedance 2.0 生成替换视频：
- 参考视频（切片后的视频片段）
- 参考图（经过 Step 1 处理后的图片）
- 替换要求（用户描述）
- 视频时长（Step 0 记录的切片时长）

### Step 3: 视频对比检查

使用 VLM 对比原视频和替换后视频，评估 5 个维度：
1. 替换完整性
2. 风格一致性
3. 视觉连贯性
4. 运镜一致性
5. 整体质量

评分 < 7.0 时自动使用改进提示词重新生成（最多重试 2 次）。

### Step 4: 视频拼接

将所有通过检查的片段按顺序拼接为最终视频，输出 `final_replaced.mp4`。

---

## CLI 使用方式

### 爆款裂变工作流

```bash
# 基本用法
python -m adsflow.main replace \
  --video https://example.com/ad.mp4 \
  --replace-images https://example.com/product.jpg \
  --requirement "将视频中的香水替换为面霜，运镜不变"

# 本地视频 + 多张替换图片
python -m adsflow.main replace \
  --video /path/to/local_ad.mp4 \
  --replace-images https://example.com/img1.jpg https://example.com/img2.jpg \
  --requirement "将视频中的手机替换为新款智能手表，保持广告叙事结构"

# 跳过对比检查
python -m adsflow.main replace \
  --video https://example.com/ad.mp4 \
  --replace-images https://example.com/product.jpg \
  --requirement "替换产品" \
  --skip-compare
```

### 广告前贴工作流

```bash
python -m adsflow.main prelude \
  --video /path/to/ad.mp4 \
  --duration 10
```

### 完整参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--video` | ✅ | 原始视频路径或公网 URL |
| `--replace-images` | ❌ | 替换图片 URL 列表（真人图片自动用 Seedream 5.0 处理） |
| `--requirement` | ✅ | 替换要求描述 |
| `--slice-duration` | ❌ | 视频切片时长（秒），默认 15 |
| `--ratio` | ❌ | 视频宽高比，默认 16:9 |
| `--resolution` | ❌ | 视频分辨率，默认 720p |
| `--no-audio` | ❌ | 不生成音频 |
| `--watermark` | ❌ | 添加水印 |
| `--skip-compare` | ❌ | 跳过视频对比检查 |
| `--compare-threshold` | ❌ | 对比检查通过阈值，默认 7.0 |
| `--compare-retries` | ❌ | 对比检查最大重试次数，默认 2 |
| `--output-dir` | ❌ | 输出目录 |

---

## 环境配置

### 1. 安装依赖

```bash
pip install -r adsflow/requirements.txt
```

### 2. 环境变量配置

在 `adsflow/.env` 文件中配置火山引擎 Ark API 密钥：

```env
ARK_API_KEY=your_ark_api_key
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
SEEDANCE_MODEL_ID=doubao-seedance-2-0-260128
SEEDANCE_FAST_MODEL_ID=doubao-seedance-2-0-fast-260128
VLM_MODEL_ID=doubao-seed-2-0-pro-260215
SEEDREAM_MODEL_ID=doubao-seedream-5-0-260128
```

### 3. 系统依赖

- **ffmpeg**：视频切片、拼接、音频处理（`brew install ffmpeg`）
- **python3**：Python 3.10+

---

## 资源说明

### adsflow/
- `config.py`：配置管理（API Key、模型 ID、参数阈值）
- `logger.py`：日志模块
- `templates.py`：提示词模板（图片识别、Seedream 重新生成、视频生成、视频对比）
- `seedance_client.py`：Seedance 2.0 + Seedream 5.0 客户端（VLM 对话、图片识别、图生图、视频生成、视频编辑、视频对比）
- `ffmpeg_ops.py`：FFmpeg 视频操作（切片、拼接、截取、音频提取/合成）
- `replace_flow.py`：爆款裂变工作流（5 步流程）
- `prelude_flow.py`：广告前贴工作流
- `main.py`：CLI 入口

### adsflow/output/
- 生成的视频片段和最终成片

---

## 失败处理

- **Seedream 5.0 不可用**：自动降级为直接使用原始替换图片，不影响工作流继续执行。
- **视频生成超时**：默认超时 600 秒，超时后抛出异常，可调整 `POLL_TIMEOUT` 配置。
- **对比检查未通过**：自动使用改进提示词重新生成，最多重试 2 次。
- **ffmpeg 未安装**：提示用户安装 ffmpeg（`brew install ffmpeg`）。
- **API Key 无效**：提示用户检查 `.env` 文件中的 `ARK_API_KEY` 配置。
