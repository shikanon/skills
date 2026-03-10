# 小红书热门内容生成器

自动生成小红书热门图文内容的工具。

## 依赖

本项目依赖 [xiaohongshu-skills](https://github.com/autoclaw-cc/xiaohongshu-skills) 提供小红书的登录、搜索和发布能力。`xiaohongshu-skills` 作为 git 子模块位于 `skills/xiaohongshu-skills`。

克隆父仓库时请使用：
```bash
git clone --recursive <repo-url>
```

如果已经克隆，请初始化子模块：
```bash
git submodule update --init --recursive
```

## 安装

### 快速开始

```bash
./install.sh
```

### 手动安装

1. 创建虚拟环境
2. 安装依赖: `pip install -r requirements.txt`
3. 配置环境变量: 复制 `.env.example` 为 `.env` 并填写配置，特别注意 `XIAOHONGSHU_COOKIES`

## 配置

编辑 `.env` 文件，填写必要的 API 密钥和 Cookies：

```env
ARK_API_KEY=your_ark_api_key
TOS_ACCESS_KEY=your_tos_access_key
TOS_SECRET_KEY=your_tos_secret_key
XIAOHONGSHU_COOKIES=your_xiaohongshu_cookies
```

## 使用

### 基础使用

```bash
source xiaohongshu-hot-content-generator-venv/bin/activate
python scripts/generate_content.py
```

### 自动发布到小红书

配置好 `XIAOHONGSHU_COOKIES` 后，可以自动发布生成的内容：

```bash
python scripts/generate_content.py --publish
```

## 小红书发布与认证

本项目整合了 [xiaohongshu-skills](https://github.com/autoclaw-cc/xiaohongshu-skills) 的能力。

### 认证方式

1. **Cookies 注入 (推荐)**: 在 `.env` 中配置 `XIAOHONGSHU_COOKIES`，脚本会自动注入到自动化浏览器中。
2. **扫码登录**: 如果 Cookies 失效，可以进入 `skills/xiaohongshu-skills` 目录运行 `python scripts/cli.py login` 进行扫码。

## 功能特性

- 联网搜索 (基于小红书热门笔记)
- 多阶段内容生成（策划 -> 文案 -> 图片）
- 生成 4K 分辨率图片
- 图片质量校验
- 输出小红书文案和标签
- 自动发布到小红书（可选）

## 测试方案

### 前置条件

1. 已完成项目安装（运行 `./install.sh`）
2. `.env` 文件配置好必要的密钥：
   - `ARK_API_KEY`: 火山引擎大模型 API 密钥
   - `TOS_ACCESS_KEY`: 对象存储访问密钥
   - `TOS_SECRET_KEY`: 对象存储密钥
   - `XIAOHONGSHU_COOKIES`: 小红书登录 Cookies（如需发布功能）

### 测试步骤

#### 1. 基本功能测试（不发布）

```bash
source xiaohongshu-hot-content-generator-venv/bin/activate
python scripts/generate_content.py --topic "AI写文案"
```

**预期结果：**
- ✅ 搜索相关案例成功
- ✅ 多阶段内容生成（策划、文案、图片提示词）正常执行
- ✅ 图片生成成功并上传到 TOS
- ✅ 内容发送到飞书（如配置）
- ✅ 最终输出提示生成完成

#### 2. 自动发布测试（需配置 XIAOHONGSHU_COOKIES）

```bash
python scripts/generate_content.py --topic "AI写文案" --publish
```

**预期结果：**
- ✅ 所有基本功能正常执行
- ✅ 内容成功发布到小红书
- ✅ 终端显示"🎉 小红书热门图文生成并发布完成！"

### 验证点

1. **图片合规性**：检查生成的图片中是否包含"小红书"字样
2. **文案质量**：标题（15字内，带emoji）、文案（口语化，分点）、标签（6-10个）
3. **图片生成**：3张图片均成功生成，分辨率为4K
4. **上传TOS**：所有资源（JSON配置、图片）均成功上传到火山引擎TOS

### 常见问题

- **缺少依赖**：运行 `pip install -r requirements.txt`
- **搜索失败**：检查 xiaohongshu-skills 子模块是否正确初始化
- **图片生成失败**：检查 ARK_API_KEY 是否正确配置
- **发布失败**：检查 XIAOHONGSHU_COOKIES 是否有效
