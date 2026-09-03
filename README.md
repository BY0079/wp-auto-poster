# WordPress 自动发文（GitHub Actions + 硅基流动）

完全免费、零服务器、零维护的 WordPress 自动发文方案。

## 工作原理

```
GitHub Actions（每 6 小时）
    ↓
调用硅基流动 DeepSeek V3 生成文章
    ↓
通过 WordPress REST API 发布为草稿
    ↓
你在 WordPress 后台审核 → 发布
```

## 费用

- ✅ GitHub Actions：每月 2,000 分钟免费额度
- ✅ 硅基流动：注册即送免费额度
- ✅ WordPress REST API：内置免费

## 部署步骤

1. 创建 GitHub 私有仓库，上传所有文件
2. 仓库 Settings → Secrets and variables → Actions 添加：
   - `WP_SITE_URL`：你的 WordPress 地址，如 `https://wordpress-41319.wasmer.app`
   - `WP_USERNAME`：WordPress 管理员用户名
   - `WP_APP_PASSWORD`：WordPress 应用密码（用户 → 个人资料 → 应用密码生成）
   - `SILICONFLOW_API_KEY`：硅基流动 API Key
   - `POST_STATUS`（可选）：`draft`（默认）/`publish`/`pending`
3. 启用 Workflows
4. 可手动测试一次：Actions → WP Auto Poster → Run workflow

## 调整发文频率

编辑 `.github/workflows/auto-post.yml`：

```yaml
schedule:
  - cron: '0 0,6,12,18 * * *'   # 每天 0/6/12/18 点（UTC 时间）
  # - cron: '0 2 * * *'         # 每天北京时间 10 点
  # - cron: '0 */6 * * *'       # 每 6 小时一次
```

> ⚠️ GitHub Actions 使用 UTC 时区，CRON 时间 +8 = 北京时间

## 修改主题

编辑 `scripts/topics.txt`，每行一个主题。

## 切换 AI 模型

修改 `scripts/auto_post.py` 第 32 行：

```python
SILICONFLOW_MODEL = "deepseek-ai/DeepSeek-V3"
# 备选模型：
# "Qwen/Qwen2.5-72B-Instruct"
# "Pro/THUDM/glm-4-9b-chat"
```
