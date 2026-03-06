# AI Movie Generator (AI 电影生成器)

基于大语言模型协作的自动化 AI 电影生成技能。支持剧本分析、角色设计、分镜生成、视频拼接全流程。

## 核心角色
- **导演 (Director)**：解析剧本，规划分镜，设定节奏。
- **角色设计师 (Character Designer)**：创作精细的角色概念图和视觉风格。
- **分镜设计师 (Storyboard Designer)**：基于导演和角色设计，生成首帧分镜图和动态视频提示词。
- **剪辑师 (Editor)**：将所有生成的分镜视频拼接成完整的短片。

## 快速开始
1. 配置 `.env` 文件，填写 `ARK_API_KEY`。
2. 运行脚本：
```bash
python3 -m scripts.generate_content --script "在遥远的星球上，一位年轻的宇航员发现了一个古老的秘密..."
```

## 技术栈
- **LLM**: 火山引擎 Ark (Doubao)
- **Image/Video Gen**: 火山引擎 Seedream/Video Generation
- **Database**: SQLite
- **Tools**: ffmpeg (可选，用于视频拼接)

## 目录结构
- `scripts/`: 核心逻辑实现
- `data/`: 角色和分镜数据库存储
- `output/`: 生成的图片、视频和最终成片
- `references/`: 角色设计风格参考指南
- `SKILL.md`: 技能元数据与 OpenClaw 兼容性定义
