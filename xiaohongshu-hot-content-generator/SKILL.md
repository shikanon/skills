---
name: xiaohongshu-hot-content-generator
description: 自动生成小红书热门图文内容的技能，支持搜索商业化变现案例、拆分生成图文prompt、生成4K分辨率图片、图片质量校验、最终输出小红书文案和标签。当用户需要生成小红书图文内容、运营小红书账号、制作商业化相关的小红书内容时使用此技能。
---

# 小红书热门图文生成器

## Overview
本技能实现全自动化的小红书热门图文生成流程，从案例搜索、内容拆分、图片生成、质量校验到最终输出文案标签，一站式完成小红书内容制作。

## 工作流程 (按顺序执行)
### Step 1: 搜索相关案例
使用web_search工具搜索网上和OpenClaw商业化、变现相关的成功案例，优先选择新颖、数据好（高赞、高收藏）的案例，排除已经使用过的案例。

### Step 2: 拆分生成图文Prompt
将选中的案例输入大模型进行分析拆分，生成逻辑清晰的图文结构，包含2-4张图片的prompt，格式为JSON：
```json
{
  "images": [
    {
      "index": 1,
      "prompt": "图片1的详细描述，包含风格、元素、构图、色彩要求",
      "title": "图片1对应的小标题"
    },
    {
      "index": 2,
      "prompt": "图片2的详细描述",
      "title": "图片2对应的小标题"
    }
  ],
  "copy": "小红书正文文案",
  "tags": ["标签1", "标签2", "标签3"]
}
```
要求prompt符合4K分辨率生成要求，描述足够具体，符合小红书热门内容风格。

### Step 3: 生成4K图片
调用图片生成技能`image-generate`，将每个图片的prompt传入，生成4K分辨率的图片，保存到本地临时目录。

### Step 4: 图片质量校验
对生成的所有图片进行检查：
1. 图片内容是否符合prompt描述
2. 视觉效果是否美观、有吸引力
3. 是否符合小红书平台风格，有引发关注的潜力
如果有任何一张图片不合格，回到Step 2重新调整prompt生成。

### Step 5: 输出最终内容
所有图片合格后，将图片、文案、标签发送到指定的飞书会话中，文案格式按照小红书热门风格排版。

## 环境配置
### 方式一：使用 pyenv (推荐)
```bash
# 1. 确保已安装 pyenv 和 pyenv-virtualenv
brew install pyenv pyenv-virtualenv

# 2. 创建虚拟环境
pyenv virtualenv 3.11 xiaohongshu-hot-content-generator
pyenv local xiaohongshu-hot-content-generator

# 3. 安装依赖
pip install -r requirements.txt
```

### 方式二：直接安装依赖
```bash
pip install -r requirements.txt
```

### 环境变量配置
在项目根目录创建 `.env` 文件：
```env
ARK_API_KEY=your_ark_api_key
TOS_ACCESS_KEY=your_tos_access_key
TOS_SECRET_KEY=your_tos_secret_key
```

### 运行脚本
```bash
python3 scripts/generate_content.py
```

## 资源说明
### scripts/
- `generate_content.py`：主流程执行脚本，实现上述完整工作流

### references/
- `xiaohongshu_style_guide.md`：小红书热门内容风格指南，包含文案、图片、标签的优秀案例和规范
