# 小红书热门内容生成器

自动生成小红书热门图文内容的工具。

## 子模块

本项目使用 [Agent-Reach](https://github.com/Panniantong/Agent-Reach) 作为 git 子模块，提供多平台内容访问和发布能力。

克隆项目时请使用：
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
3. 配置环境变量: 复制 `.env.example` 为 `.env` 并填写配置

## 更新

```bash
./update.sh
```

## 配置

编辑 `.env` 文件，填写必要的 API 密钥：

```env
ARK_API_KEY=your_ark_api_key
TOS_ACCESS_KEY=your_tos_access_key
TOS_SECRET_KEY=your_tos_secret_key
```

## 使用

### 基础使用

```bash
source xiaohongshu-hot-content-generator-venv/bin/activate
python scripts/generate_content.py
```

### 自动发布到小红书

配置好发布环境后，可以自动发布生成的内容：

```bash
python scripts/generate_content.py --publish
```

### 查看发布配置指南

```bash
python scripts/generate_content.py --setup-guide
```

## 小红书发布功能

本项目整合了 [Agent-Reach](https://github.com/Panniantong/Agent-Reach) 的小红书发布能力，通过 [xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp) 实现。

### 配置步骤

1. 安装 Docker
2. 安装 mcporter: `npm install -g mcporter`
3. 启动 xiaohongshu-mcp 服务
4. 扫码登录
5. 运行脚本时添加 `--publish` 参数

详细配置指南请运行: `python scripts/generate_content.py --setup-guide`

## 功能特性

- 联网搜索
- 拆分生成图文 prompt
- 生成 4K 分辨率图片
- 图片质量校验
- 输出小红书文案和标签
- 自动发布到小红书（可选）
