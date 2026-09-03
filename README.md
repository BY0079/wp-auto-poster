# WordPress 自动发文系统 v2.0

基于 **GitHub Actions + 硅基流动 DeepSeek V3 + WordPress REST API** 的零成本自动发文方案。

## ✨ 特性

- 🕗 **每天北京时间 8:00** 准时自动发布
- 🤖 **DeepSeek V3** AI 写作，1000-1500 字高质量内容
- 📊 **SEO 优化**：标题含关键词、文前概况、结构化正文、标签、友好 slug
- 🎯 **降低 AI 味**：避免模板句、多用具体案例、口语化表达
- 🏷️ **6 个分类**：云服务器与建站 / AI 与效率 / WordPress 建站 / 编程开发 / 新手入门 / 数字生活
- 🌐 **主题相关推广**：云服务器类文章才推雨云，**自然不硬广**
- 📝 **自动标签**：AI 提取关键词自动创建 WordPress 标签

## 📂 文件结构

```
wp-autoposter/
├── .github/workflows/auto-post.yml   # GitHub Actions 配置
├── auto_post.py                      # 主脚本（SEO + 推广 + 分类）
├── topics.json                       # 30 个主题 + 分类 + 推广标记
├── scripts/requirements.txt          # Python 依赖
└── README.md                         # 本文档
```

## 🔑 GitHub Secrets 配置

| Secret | 说明 |
|--------|------|
| `WP_SITE_URL` | WordPress 站点 URL，如 `https://example.com` |
| `WP_USERNAME` | WordPress 管理员账号 |
| `WP_USER_PWD` | WordPress Application Password（**去空格**） |
| `SF_USER_TOKEN` | 硅基流动 API Key |
| `POST_STATUS` | `publish`（自动发布）/ `draft`（草稿） |

## 🚀 使用方法

### 1. WordPress 后台

- 创建 6 个分类（名字必须和 `topics.json` 里的 `category` 字段一致）
- 用户 → Profile → Application Passwords → 生成一个新密码

### 2. GitHub

- 推送代码到仓库
- Settings → Secrets → 配置上述 5 个 Secret
- Actions → Run workflow 测试

### 3. 触发频率

GitHub Actions 的 cron 用 UTC 时间，**北京时间 8:00 = UTC 0:00**：

```yaml
schedule:
  - cron: '0 0 * * *'    # 每天 UTC 0:00（北京时间 8:00）
```

## 📝 topics.json 结构

每个主题包含：
```json
{
  "title": "文章标题",
  "category": "分类名（必须与 WordPress 后台一致）",
  "promo": true,           // true=推雨云，false=不推
  "keywords": ["关键词1", "关键词2"],
  "reason": "为什么这个主题要/不要推广"
}
```

当前推广分布：
- ☁️ 云服务器与建站（5 个）→ **全部推**
- 🤖 AI 与效率（5 个）→ 不推
- 📝 WordPress 建站（5 个）→ 不推
- 💻 编程开发（5 个）→ 不推
- 🌱 新手入门（5 个）→ 不推
- 🌐 数字生活（5 个）→ 不推

推广频率：30 篇里 5 篇 = **约每 6 篇一次**（更自然）

## 🎨 SEO 优化要点

### 标题
- 15-28 字，含主关键词
- 数字/悬念/对比/痛点

### 全文概况（100-200 字）
- 放在文前，**样式化的蓝色框**
- 3 秒让读者判断文章价值

### 正文
- H2/H3 结构化
- 短段落（≤4 行/段）
- 列表、引用、粗体
- 至少 1 个具体案例

### AI 味淡化
- ❌ 禁止：「作为...」「综上所述」「首先...其次...最后」
- ✅ 多用「我」「你」，具体数字，口语化，反问句

## 🔧 本地调试

```bash
pip install -r scripts/requirements.txt

export WP_SITE_URL="https://your-site.com"
export WP_USERNAME="admin"
export WP_USER_PWD="your app password"
export SF_USER_TOKEN="sk-xxx"
export POST_STATUS="publish"

python auto_post.py
```

## 📜 License

MIT