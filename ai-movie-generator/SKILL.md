---
name: ai-movie-generator
description: 基于大模型的AI电影生成器，支持多角色LLM协作。包含导演、角色设计师、分镜设计师、剪辑师四个核心角色。自动解析剧本、设计角色概念图、生成分镜视频并最终拼接成完整的AI短片。内置LLM任务执行管家，记录和检查每步任务完成情况，确保流程按序执行并支持自动重试。当用户需要将文字剧本转化为动态视频内容时使用此技能。
---

# AI 电影生成器 (AI Movie Generator)

## Overview
本技能通过多个专门的大语言模型（LLM）角色协同工作，将剧本自动转化为AI生成的短片。技能集成了剧本分析、角色视觉设计、分镜生成和视频剪辑的全流程。

### LLM 任务执行管家
系统内置完整的任务管理框架，提供以下功能：
- **任务依赖管理**：确保任务按正确顺序执行，前置任务未完成时跳过后续任务
- **自动重试机制**：任务失败时自动重试（默认3次）
- **实时状态跟踪**：记录每个任务的开始/结束时间、执行时长、状态
- **详细日志输出**：彩色日志显示任务进度（🚀开始/✅完成/❌失败/🔄重试）
- **任务摘要报告**：工作流结束后生成统计摘要和详细报告
- **JSON报告保存**：将完整任务记录保存到 `output/workflow_report.json`

### 工作流任务清单
1. `init_db` - 初始化数据库
2. `init_ai` - 初始化 AI 客户端
3. `read_script` - 读取剧本
4. `director_plan` - 导演分析剧本
5. `character_design` - 角色设计
6. `storyboard_design` - 分镜设计
7. `video_generation` - 视频生成
8. `video_editing` - 视频拼接
9. `finalization` - 最终整理

## 工作流程 (按顺序执行)

### Step 1: 剧本解析 (导演 LLM)
输入剧本文本或文件，由“大导演”进行规划。
- 提取场景、分镜、角色列表。
- 规划对话、旁白、音效和背景音乐。
- 设定分镜时长（4-12秒）。

### Step 2: 角色设计 (角色设计师 LLM)
从剧本中抽取角色并进行视觉设定。
- 存储角色信息到 SQLite 数据库（`data/movie_gen.db`）。
- 生成角色标准概念图提示词（正面、侧面、背面）。
- 生成包含细节区、主视图区、新服装区、动作区、表情区的完整设计页面。

### Step 3: 分镜规划 (分镜设计师 LLM)
基于导演的分镜描述和角色设定，生成分镜首帧图提示词。
- 确保角色视觉一致性。
- 使用图生图（i2i）逻辑或精确的提示词生成首帧图。

### Step 4: 分镜视频生成
基于生成的分镜首帧图，调用视频生成模型生成动态视频片段。

### Step 5: 视频拼接 (剪辑师 LLM & 工具)
将所有生成的分镜视频按顺序拼接。
- 保持音视频同步（取决于实现）。
- 输出最终的 MP4 文件。

## 环境配置

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 环境变量配置
在项目根目录创建 `.env` 文件，配置火山引擎（Volcengine）Ark API 密钥：
```env
ARK_API_KEY=your_ark_api_key
```

### 3. 运行脚本
```bash
# 输入文本剧本
python3 -m scripts.generate_content --script "在遥远的星球上，一位年轻的宇航员发现了一个古老的秘密..."

# 输入剧本文件
python3 -m scripts.generate_content --script "/path/to/your/script.txt"
```

## 资源说明
### scripts/
- `config.py`：基础配置与 API 初始化
- `database.py`：SQLite 数据库管理（角色与分镜存储）
- `prompts.py`：四个核心角色的系统提示词
- `generate_content.py`：主流程执行脚本

### data/
- `movie_gen.db`：SQLite 数据库文件，存储角色信息

### output/
- 生成的概念图、分镜图、视频片段和最终成片
