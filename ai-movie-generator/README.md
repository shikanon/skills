# AI Movie Generator (AI 电影生成器)

基于大语言模型协作的自动化 AI 电影生成技能。支持剧本分析、角色设计、分镜生成、视频拼接全流程。

## 核心角色
- **导演 (Director)**：解析剧本，规划分镜，设定节奏。
- **角色设计师 (Character Designer)**：创作精细的角色概念图和视觉风格。
- **分镜设计师 (Storyboard Designer)**：基于导演和角色设计，生成首帧分镜图和动态视频提示词。
- **质检智能体 (QA Inspector)**：优化提示词，防止角色崩坏，提升生成质量。
- **剪辑师 (Editor)**：将所有生成的分镜视频拼接成完整的短片。

## 快速开始
1. 配置 `.env` 文件，填写 `ARK_API_KEY`。
2. 运行脚本：
```bash
python3 -m scripts.generate_content_real --script "在遥远的星球上，一位年轻的宇航员发现了一个古老的秘密..."
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

## 功能特性
- ✅ 6步完整流程：剧本输入→导演规划→角色设计→分镜生成→视频生成→视频拼接
- ✅ 4个大模型 Agent + 1个质检智能体协作
- ✅ 好莱坞电影风格角色设计
- ✅ 图生图技术参考角色概念图生成分镜
- ✅ 智能提示词优化，防止角色崩坏
- ✅ 真实火山引擎 API 集成
- ✅ SQLite 数据库存储角色和分镜信息
- ✅ 视频生成参数优化指导
- ✅ ffmpeg 视频自动拼接

## 测试脚本
- `test_video_generation.py`: 视频生成单元测试
- `test_qa_only.py`: 质检智能体测试
