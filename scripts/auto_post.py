#!/usr/bin/env python3
"""
WordPress 自动发文脚本
- 通过硅基流动 DeepSeek API 生成文章
- 通过 WordPress REST API 发布为草稿
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


# ============ 配置区 ============
WP_SITE_URL = os.environ.get("WP_SITE_URL", "").rstrip("/")
WP_USERNAME = os.environ.get("WP_USERNAME", "")
WP_USER_PWD = os.environ.get("WP_USER_PWD", "").replace(" ", "")
SF_USER_TOKEN = os.environ.get("SF_USER_TOKEN", "")
POST_STATUS = os.environ.get("POST_STATUS", "draft")
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
SILICONFLOW_MODEL = "deepseek-ai/DeepSeek-V3"

# 主题文件路径
TOPICS_FILE = Path(__file__).parent / "topics.txt"
STATE_FILE = Path(__file__).parent / "state.json"


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
    """加载主题列表"""
    if not TOPICS_FILE.exists():
        log(f"WARN: Topics file {TOPICS_FILE} not found, using defaults")
        return ["AI and Daily Life", "Tech Trends", "Productivity Tools"]
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        topics = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    log(f"OK: Loaded {len(topics)} topics")
    return topics


def load_state() -> dict:
    """加载上次运行状态"""
    if not STATE_FILE.exists():
        return {"used": []}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"used": []}


def save_state(state: dict) -> None:
    """保存运行状态"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def pick_topic(topics: list, state: dict) -> str:
    """选择主题：优先选择未使用过的"""
    used = set(state.get("used", []))
    available = [t for t in topics if t not in used]
    if not available:
        log("INFO: All topics used, resetting usage record")
        state["used"] = []
        available = topics
    topic = random.choice(available)
    state["used"].append(topic)
    return topic


def generate_article(topic: str) -> dict:
    """调用硅基流动 API 生成文章"""
    log(f"INFO: Generating article: {topic}")

    system_prompt = """You are a senior SEO content editor, specializing in writing clear, reader-friendly Chinese articles.

Requirements:
1. Title should be 15-25 characters, include keywords, attract clicks
2. Article 800-1500 words
3. Use H2/H3 headings, clear structure
4. Short paragraphs, no more than 4 lines each
5. Use lists, quotes, bold formatting appropriately
6. Content should be practical and in-depth, no fluff
7. Output in HTML format (NOT Markdown)
8. Do NOT write 'Title:' prefix at the beginning

Output format (strictly follow):
First line is the title (plain text, no # symbols)
Empty line
Then the HTML body of the article"""

    user_prompt = f"""Please write a high-quality SEO blog article on the topic: '{topic}'

Requirements:
- Target audience: General users interested in the topic
- Tone: Professional but approachable
- Include: Background, key points, practical advice, summary
- Length: 1000-1500 words
- Output in HTML format (use <h2>, <h3>, <p>, <ul>, <li>, <strong> tags)"""

    headers = {
        "Authorization": f"Bearer {SF_USER_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": SILICONFLOW_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 4096
    }

    try:
        resp = requests.post(
            f"{SILICONFLOW_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        log(f"OK: AI generation succeeded, chars: {len(content)}")

        # 解析标题和正文
        lines = content.split("\n", 1)
        if len(lines) >= 2 and lines[0].strip():
            title = lines[0].strip().strip("#").strip()
            body = lines[1].strip()
        else:
            # 兜底：提取 <h1> 或前 50 字
            m = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.DOTALL | re.IGNORECASE)
            if m:
                title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
                body = content
            else:
                title = topic
                body = content

        # 清理标题里的引号
        title = title.strip("\"'""''「」")

        return {"title": title, "content": body}
    except requests.exceptions.Timeout:
        log("ERROR: AI generation timeout (>120s)")
        sys.exit(1)
    except Exception as e:
        log(f"ERROR: AI generation failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            log(f"  Response: {e.response.text[:500]}")
        sys.exit(1)


def post_to_wordpress(title: str, content: str, topic: str) -> dict:
    """通过 WordPress REST API 发布文章"""
    log(f"INFO: Posting to WordPress: {title}")

    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/posts"

    # 构造 slug
    slug = re.sub(r"[^\w\s-]", "", topic.lower())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")[:50]

    payload = {
        "title": title,
        "content": content,
        "status": POST_STATUS,
        "slug": slug,
        "excerpt": content[:200].replace("<", " ").replace(">", " ")
    }

    try:
        resp = requests.post(
            endpoint,
            auth=(WP_USERNAME, WP_USER_PWD),
            json=payload,
            timeout=30
        )
        log(f"DEBUG: HTTP Status = {resp.status_code}")
        log(f"DEBUG: Content-Type = {resp.headers.get('Content-Type', 'N/A')}")
        log(f"DEBUG: Response body (first 500 chars):")
        log(f"  {resp.text[:500]}")

        # wasmer.io 的 WordPress 会在 JSON 前面插入 PHP Warning HTML
        # 容错提取：找到第一个 { 开始和最后一个 } 结束
        text = resp.text.strip()
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            clean_json = text[json_start:json_end]
            post = json.loads(clean_json)
            log(f"OK: Post published! ID: {post.get('id')}")
            log(f"  Status: {post.get('status')}")
            log(f"  Link: {post.get('link')}")
            return post
        else:
            log("ERROR: Could not find JSON in response")
            sys.exit(1)
    except requests.exceptions.HTTPError as e:
        log(f"ERROR: WordPress publish failed: {e.response.status_code}")
        log(f"  Response: {e.response.text[:500]}")
        sys.exit(1)
    except Exception as e:
        log(f"ERROR: WordPress publish failed: {e}")
        log(f"  Response body (first 500 chars): {resp.text[:500] if 'resp' in locals() else 'N/A'}")
        sys.exit(1)


def main() -> None:
    log("=" * 50)
    log("START: WordPress Auto Post Script")

    # 1. 检查环境
    check_env()

    # 2. 加载主题
    topics = load_topics()

    # 3. 选择主题
    state = load_state()
    topic = pick_topic(topics, state)
    log(f"INFO: This run topic: {topic}")

    # 4. 生成文章
    article = generate_article(topic)
    log(f"INFO: Title: {article['title']}")

    # 5. 发布到 WordPress
    post = post_to_wordpress(article["title"], article["content"], topic)

    # 6. 保存状态
    save_state(state)

    log("=" * 50)
    log("DONE: All complete!")
    log(f"  Post ID: {post.get('id')}")
    log(f"  Status: {post.get('status')}")


if __name__ == "__main__":
    main()