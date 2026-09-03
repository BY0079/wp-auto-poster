#!/usr/bin/env python3
"""
WordPress 自动发文脚本 v2.1
- 模型：Qwen/Qwen2.5-72B-Instruct（中文写作最自然，AI 味最低）
- SEO 优化：标题含关键词、文前概况、外链题图、正文结构化、标签、英文 slug
- AI 味淡化：具体场景、口语化、避免模板句
- 主题相关推广：云服务器类主题才推雨云
- 每天北京时间 8:00 自动发布

环境变量（GitHub Secrets）:
- WP_SITE_URL: WordPress 站点 URL
- WP_USERNAME: 管理员账号
- WP_USER_PWD: WordPress Application Password（去空格）
- SF_USER_TOKEN: 硅基流动 API Key
- POST_STATUS: draft | publish（默认 publish）
- TEST_FORCE_PROMO: 仅用于测试，强制选 promo 主题（true/false）
"""

import os
import sys
import json
import random
import re
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: Missing 'requests' library. Run: pip install requests")
    sys.exit(1)


# ============ 配置 ============
WP_SITE_URL = os.environ.get("WP_SITE_URL", "").rstrip("/")
WP_USERNAME = os.environ.get("WP_USERNAME", "")
WP_USER_PWD = os.environ.get("WP_USER_PWD", "").replace(" ", "")
SF_USER_TOKEN = os.environ.get("SF_USER_TOKEN", "")
POST_STATUS = os.environ.get("POST_STATUS", "publish")
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
SILICONFLOW_MODEL = "Qwen/Qwen2.5-72B-Instruct"

# 测试模式：强制选 promo=true 的主题
TEST_FORCE_PROMO = os.environ.get("TEST_FORCE_PROMO", "").lower() == "true"

TOPICS_FILE = Path(__file__).parent / "topics.json"
STATE_FILE = Path(__file__).parent / "state.json"


# ============ 推广块（雨云服务器，主题相关才插入） ============
RAINYUN_PROMO_HTML = """
<hr>
<aside style="background: #fff8f5; border-left: 4px solid #ff6b35; padding: 18px 22px; margin: 28px 0; border-radius: 6px;">
<p style="margin: 0 0 10px 0; font-size: 16px;"><strong>🚀 推荐雨云服务器</strong></p>
<p style="margin: 0 0 10px 0; line-height: 1.7;">雨云是主打高性价比的国内云服务商，新人用优惠码 <code style="background:#fff; padding:2px 8px; border-radius:3px; color:#ff6b35; font-weight:bold;">aabh</code> 可以拿到 <strong style="color:#ff6b35;">首月 5 折</strong>，还支持 <strong>7 天无理由退款</strong>，试错成本很低。</p>
<p style="margin: 0;"><a href="https://www.rainyun.com/aabh_" target="_blank" rel="nofollow noopener" style="color:#ff6b35; text-decoration:none; font-weight:bold;">👉 立即领取优惠 →</a></p>
</aside>
"""


def log(msg: str) -> None:
    """统一日志输出"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def check_env() -> None:
    """检查必要的环境变量"""
    missing = []
    if not WP_SITE_URL:
        missing.append("WP_SITE_URL")
    if not WP_USERNAME:
        missing.append("WP_USERNAME")
    if not WP_USER_PWD:
        missing.append("WP_USER_PWD")
    if not SF_USER_TOKEN:
        missing.append("SF_USER_TOKEN")
    if missing:
        log(f"ERROR: Missing env vars: {', '.join(missing)}")
        sys.exit(1)
    log("OK: Environment variables validated")


def load_topics() -> list:
    """加载主题列表（从 topics.json）"""
    if not TOPICS_FILE.exists():
        log(f"ERROR: Topics file {TOPICS_FILE} not found")
        sys.exit(1)
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    topics = data.get("topics", [])
    log(f"OK: Loaded {len(topics)} topics")
    return topics


def load_state() -> dict:
    """加载上次运行状态"""
    if not STATE_FILE.exists():
        return {"used_topics": [], "last_run": None, "total_runs": 0}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"used_topics": [], "last_run": None, "total_runs": 0}


def save_state(state: dict) -> None:
    """保存运行状态"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def pick_topic(topics: list, state: dict) -> dict:
    """选择主题：优先未使用过的"""
    used = set(state.get("used_topics", []))

    if TEST_FORCE_PROMO:
        log("INFO: TEST_FORCE_PROMO=true, only selecting promo topics")
        candidates = [t for t in topics if t.get("promo") and t["title"] not in used]
        if not candidates:
            candidates = [t for t in topics if t.get("promo")]
    else:
        candidates = [t for t in topics if t["title"] not in used]

    if not candidates:
        log("INFO: All topics used, resetting usage record")
        state["used_topics"] = []
        if TEST_FORCE_PROMO:
            candidates = [t for t in topics if t.get("promo")]
        else:
            candidates = topics

    topic = random.choice(candidates)
    state["used_topics"].append(topic["title"])
    return topic


def get_categories_map() -> dict:
    """获取 WordPress 分类 ID 映射 {分类名: ID}"""
    try:
        resp = requests.get(
            f"{WP_SITE_URL}/wp-json/wp/v2/categories",
            params={"per_page": 100},
            timeout=30,
        )
        resp.raise_for_status()
        cats = resp.json()
        cat_map = {c["name"]: c["id"] for c in cats}
        log(f"OK: Fetched {len(cat_map)} categories")
        for name, cid in cat_map.items():
            log(f"  - {name} (ID={cid})")
        return cat_map
    except Exception as e:
        log(f"ERROR: Failed to fetch categories: {e}")
        sys.exit(1)


def generate_article(topic: dict) -> dict:
    """调用硅基流动 API 生成文章

    返回结构: {title, summary, slug, content, keywords}
    """
    log(f"INFO: Generating article: {topic['title']}")
    log(f"  Category: {topic['category']}")
    log(f"  Promo: {topic.get('promo', False)}")

    system_prompt = """你是一位有 8 年经验的中文 SEO 博主，擅长写云服务器、AI 工具、WordPress 建站、编程开发、新手入门等领域的高质量原创文章。你写的文章经常排在搜索引擎前 3 名。

# 写作要求

## 1. 标题
- 15-28 字，必须包含主关键词
- 吸引点击：用具体数字、对比、痛点、悬念
- 例：「域名注册从入门到精通：新手必知的 5 个避坑点」

## 2. 全文概况（必须，100-200 字）
- 放在文章最前面，用一段连续文字
- 概括文章核心要点，让读者 3 秒判断价值
- 自然融入主关键词

## 3. 题图（必须）
- 在「全文概况」之后、「正文」之前，插入一张外链图片
- 图片格式：
  <img src="https://tuimeizi.cn/pure/宽度x高度" alt="关键词" style="max-width:100%;height:auto;border-radius:8px;margin:0 0 24px 0;" />
- 宽度随机 600-900，高度随机 200-900（例如 743x518）
- alt 用主关键词

## 4. 正文（1500-2500 字）
- H2 / H3 结构化
- 短段落（每段 2-4 句）
- 列表、引用、粗体合理使用
- 至少 2 个具体案例或真实经验
- 适度加入数据（具体数字，不要"很多"）
- 文末小结或行动建议

## 5. 降低 AI 味（非常重要）
- 禁止：「作为...」「综上所述」「总而言之」「首先...其次...最后」「值得注意的是」「不得不承认」「在当今社会」
- 多用第一人称「我」「我们」或第二人称「你」
- 口语化、有温度，像老朋友分享经验
- 可以吐槽、可以幽默、可以用反问
- 段落长短不均，模拟真人写作节奏
- 具体场景：「去年我帮朋友选服务器...」「踩过坑才懂...」

## 6. SEO 优化
- 标题、概况、小标题、正文都自然包含主关键词
- 关键词密度 2-3%，不要堆砌
- 内部逻辑清晰，利于搜索引擎理解

## 7. 英文 slug
- 输出 SLUG 字段：用短横线连接的英文关键词，不超过 60 字符
- 例：best-cloud-server-2026、wordpress-seo-guide、deepseek-v3-review

## 8. 输出格式（严格按此格式）

```
TITLE: <标题>
SUMMARY: <100-200字概览，一段连续文字，含主关键词>
SLUG: <english-slug-here>
KEYWORDS: <关键词1, 关键词2, 关键词3>
CONTENT:
<HTML正文：开头题图img标签 + 概况(如果概况不在CONTENT里) + H2/H3/p/ul/li/blockquote，不要Markdown的#号>
```

不要任何前言、寒暄、解释，直接按格式输出。"""

    user_prompt = f"""请写一篇关于「{topic['title']}」的高质量 SEO 原创博客文章。

- 目标读者：对 {topic['category']} 感兴趣的用户
- 主关键词：{', '.join(topic['keywords'])}
- 必须包含：
  * 全文概况 100-200 字（含主关键词）
  * 题图（外链 tuimeizi.cn，宽度 600-900，高度 200-900 随机）
  * 2-4 个 H2 小标题
  * 1-2 个列表或表格
  * 至少 2 个具体案例或个人经验
  * 文末小结或行动建议
- 字数：1500-2500 字
- 语气：专业但接地气，像资深博主分享真实经验
- 降低 AI 味：不用模板句、多具体数字、口语化

请严格按格式输出。"""

    headers = {
        "Authorization": f"Bearer {SF_USER_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": SILICONFLOW_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 6144,
    }

    try:
        resp = requests.post(
            f"{SILICONFLOW_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=240,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        log(f"OK: AI generation succeeded, raw chars: {len(content)}")

        return parse_ai_output(content, topic)
    except requests.exceptions.Timeout:
        log("ERROR: AI generation timeout (>240s)")
        sys.exit(1)
    except Exception as e:
        log(f"ERROR: AI generation failed: {e}")
        sys.exit(1)


def parse_ai_output(content: str, topic: dict) -> dict:
    """解析 AI 输出的结构化数据"""
    result = {"title": "", "summary": "", "slug": "", "keywords": [], "content": ""}

    # TITLE
    m = re.search(r"TITLE:\s*(.+?)(?=\n(?:SUMMARY|SLUG|KEYWORDS|CONTENT):|$)", content, re.DOTALL)
    if m:
        result["title"] = m.group(1).strip()

    # SUMMARY
    m = re.search(r"SUMMARY:\s*(.+?)(?=\n(?:TITLE|SLUG|KEYWORDS|CONTENT):|$)", content, re.DOTALL)
    if m:
        result["summary"] = m.group(1).strip()

    # SLUG
    m = re.search(r"SLUG:\s*(.+?)(?=\n(?:TITLE|SUMMARY|KEYWORDS|CONTENT):|$)", content, re.DOTALL)
    if m:
        result["slug"] = m.group(1).strip().lower()

    # KEYWORDS
    m = re.search(r"KEYWORDS:\s*(.+?)(?=\n(?:TITLE|SUMMARY|SLUG|CONTENT):|$)", content, re.DOTALL)
    if m:
        result["keywords"] = [k.strip() for k in m.group(1).split(",") if k.strip()]

    # CONTENT
    m = re.search(r"CONTENT:\s*(.+)$", content, re.DOTALL)
    if m:
        result["content"] = m.group(1).strip()

    # 兜底
    if not result["content"]:
        log("WARN: Could not parse CONTENT, fallback to whole response")
        result["content"] = content
    if not result["title"]:
        result["title"] = topic["title"]
    if not result["summary"] and result["content"]:
        text = re.sub(r"<[^>]+>", "", result["content"])
        result["summary"] = text[:200].strip() + "..."
    if not result["slug"]:
        result["slug"] = re.sub(r"[^\w\s-]", "", result["title"].lower()).replace(" ", "-")[:50]

    log(f"  Title: {result['title']}")
    log(f"  Summary chars: {len(result['summary'])}")
    log(f"  Slug: {result['slug']}")
    log(f"  Keywords: {result['keywords']}")
    log(f"  Content chars: {len(result['content'])}")
    log(f"  Has img tag: {'<img' in result['content'].lower()}")

    return result


def build_html_content(article: dict, topic: dict) -> str:
    """组装完整 HTML：概览 + 正文（含题图） + 推广块（如果主题相关）"""
    parts = []

    # 全文概况块
    summary_block = (
        '<div class="article-summary" '
        'style="background: #f0f7ff; border-left: 4px solid #4a90e2; '
        'padding: 18px 22px; margin: 0 0 28px 0; border-radius: 6px;">'
        '<p style="margin: 0; color: #333; font-size: 15.5px; '
        'line-height: 1.75;"><strong>📋 全文概况：</strong>'
        f'{article["summary"]}'
        '</p></div>'
    )
    parts.append(summary_block)

    # 正文（开头已包含 AI 生成的题图 img 标签）
    parts.append(article["content"])

    # 推广块（主题相关才加）
    if topic.get("promo"):
        parts.append(RAINYUN_PROMO_HTML)
        log("INFO: Added Rainyun promo block (topic is cloud-server related)")
    else:
        log("INFO: No promo (topic not related to cloud server)")

    return "\n".join(parts)


def get_or_create_tags(tag_names: list) -> list:
    """获取或创建标签，返回 tag ID 列表"""
    tag_ids = []
    for name in tag_names:
        name = name.strip()[:50]
        if not name:
            continue
        try:
            resp = requests.get(
                f"{WP_SITE_URL}/wp-json/wp/v2/tags",
                params={"search": name, "per_page": 5},
                auth=(WP_USERNAME, WP_USER_PWD),
                timeout=15,
            )
            resp.raise_for_status()
            tags = resp.json()
            existing = next((t for t in tags if t["name"].lower() == name.lower()), None)
            if existing:
                tag_ids.append(existing["id"])
                continue
            resp = requests.post(
                f"{WP_SITE_URL}/wp-json/wp/v2/tags",
                auth=(WP_USERNAME, WP_USER_PWD),
                json={"name": name},
                timeout=15,
            )
            resp.raise_for_status()
            tag = resp.json()
            tag_ids.append(tag["id"])
            log(f"  Created tag: {name} (ID={tag['id']})")
        except Exception as e:
            log(f"WARN: Failed to get/create tag '{name}': {e}")
    return tag_ids


def post_to_wordpress(article: dict, topic: dict, cat_map: dict) -> dict:
    """发布文章到 WordPress"""
    log(f"INFO: Posting to WordPress: {article['title']}")

    cat_id = cat_map.get(topic["category"])
    if cat_id:
        log(f"  Category: {topic['category']} (ID={cat_id})")
    else:
        log(f"  WARN: Category '{topic['category']}' not found, using default")

    # 英文 slug（SEO 友好）
    slug = article.get("slug") or re.sub(r"[^\w\s-]", "", article["title"].lower()).replace(" ", "-")[:50]
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        slug = "post-" + datetime.now().strftime("%Y%m%d%H%M%S")

    # 组装完整 HTML
    full_content = build_html_content(article, topic)

    payload = {
        "title": article["title"],
        "content": full_content,
        "excerpt": article["summary"],
        "status": POST_STATUS,
        "slug": slug,
    }
    if cat_id:
        payload["categories"] = [cat_id]

    # 标签
    if article["keywords"]:
        tag_ids = get_or_create_tags(article["keywords"])
        if tag_ids:
            payload["tags"] = tag_ids

    log(f"DEBUG: POST payload keys: {list(payload.keys())}")
    log(f"DEBUG: Slug: {slug}")
    log(f"DEBUG: Status: {POST_STATUS}")

    try:
        resp = requests.post(
            f"{WP_SITE_URL}/wp-json/wp/v2/posts",
            auth=(WP_USERNAME, WP_USER_PWD),
            json=payload,
            timeout=30,
        )
        log(f"DEBUG: HTTP Status = {resp.status_code}")
        log(f"DEBUG: Content-Type = {resp.headers.get('Content-Type', 'N/A')}")

        # 容错解析 JSON（wasmer.io PHP Warning bug）
        text = resp.text.strip()
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            post = json.loads(text[json_start:json_end])
            log(f"OK: Post published!")
            log(f"  ID: {post.get('id')}")
            log(f"  Status: {post.get('status')}")
            log(f"  Link: {post.get('link')}")
            return post
        else:
            log(f"ERROR: No JSON in response. Body: {resp.text[:500]}")
            sys.exit(1)
    except requests.exceptions.HTTPError as e:
        log(f"ERROR: WordPress publish HTTP error: {e.response.status_code}")
        log(f"  Response: {e.response.text[:500]}")
        sys.exit(1)
    except Exception as e:
        log(f"ERROR: WordPress publish failed: {e}")
        if "resp" in locals():
            log(f"  Response: {resp.text[:500]}")
        sys.exit(1)


def main() -> None:
    log("=" * 60)
    log("START: WordPress Auto Post Script v2.1")
    log(f"  Model: {SILICONFLOW_MODEL}")
    if TEST_FORCE_PROMO:
        log("  Mode: TEST_FORCE_PROMO (only promo topics)")

    # 1. 检查环境
    check_env()

    # 2. 加载主题
    topics = load_topics()

    # 3. 加载状态
    state = load_state()
    state["total_runs"] = state.get("total_runs", 0) + 1

    # 4. 选择主题
    topic = pick_topic(topics, state)
    log(f"INFO: Selected topic: {topic['title']}")

    # 5. 生成文章
    article = generate_article(topic)

    # 6. 获取分类映射
    cat_map = get_categories_map()

    # 7. 发布到 WordPress
    post = post_to_wordpress(article, topic, cat_map)

    # 8. 保存状态
    state["last_run"] = datetime.now().isoformat()
    save_state(state)

    log("=" * 60)
    log("DONE: All complete!")
    log(f"  Post ID: {post.get('id')}")
    log(f"  Link: {post.get('link')}")
    log(f"  Category: {topic['category']}")
    log(f"  Promo: {topic.get('promo', False)}")
    log(f"  Total runs: {state['total_runs']}")


if __name__ == "__main__":
    main()