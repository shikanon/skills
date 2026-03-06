# 最佳Skills实践仓库

本仓库沉淀了OpenClaw平台下经过实战验证的优质技能，可直接导入使用。

## 已收录技能列表

| 技能名称 | 功能说明 |
|---------|---------|
| xiaohongshu-hot-content-generator | 自动生成小红书热门图文内容，支持搜索案例、生成4K图片、质量校验、飞书自动发送 |
| ai-movie-generator | AI 电影生成器，支持剧本分析、角色设计、分镜生成、视频拼接全流程，5个Agent协作 |
| 更多技能持续更新中... | |

## 使用说明
1. 下载对应的`.skill`技能包
2. 在OpenClaw平台导入技能包即可使用
3. 所有技能均已移除硬编码密钥，使用前请配置对应的环境变量

## 环境变量配置
使用技能前请配置以下环境变量：
- `ARK_API_KEY`: 火山引擎Ark大模型API密钥
- `MODEL_VIDEO_NAME`: 视频生成模型ID（可选，视频类技能需要）
- `VOLCENGINE_ACCESS_KEY`: 火山引擎Access Key（可选，部分服务需要）
- `VOLCENGINE_SECRET_KEY`: 火山引擎Secret Key（可选，部分服务需要）
