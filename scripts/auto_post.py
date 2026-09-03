#!/usr/bin/env python3
"""
WordPress 自动发文脚本
- 通过硅基流动 DeepSeek API 生成文章
- 通过 WordPress REST API 发布
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
    print("❌ 缺少 requests 库，请先运行: pip install requests")
    sys.exit(1)


# ============ 配置区 ============
WP_SITE_URL = os.environ.get("WP_SITE_URL", "").rstrip("/")
WP_USERNAME = os.environ.get("WP_USERNAME", "")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "").replace(" ", "")
SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "")
POST_STATUS = os.environ.get("POST_STATUS", "draft")  # draft=草稿 publish=直接发布
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
    if not WP_APP_PASSWORD:
        missing.append("WP_APP_PASSWORD")
    if not SILICONFLOW_API_KEY:
        missing.append("SILICONFLOW_API_KEY")
    if missing:
        log(f"❌ 缺少环境变量: {', '.join(missing)}")
        sys.exit(1)
    log("✅ 环境变量检查通过")


def load_topics() -> list:
    """加载主题列表"""
    if not TOPICS_FILE.exists():
        log(f"⚠️ 主题文件 {TOPICS_FILE} 不存在，使用默认主题")
        return ["人工智能与生活", "科技发展趋势", "效率工具推荐"]
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        topics = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    log(f"✅ 加载 {len(topics)} 个主题")
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
        # 全部用过了，重置
        log("🔄 所有主题已使用，重置使用记录")
        state["used"] = []
        available = topics
    topic = random.choice(available)
    state["used"].append(topic)
    return topic


def generate_article(topic: str) -> dict:
    """调用硅基流动 API 生成文章"""
    log(f"🤖 正在生成文章: {topic}")

    system_prompt = """你是一名资深的 SEO 内容编辑，擅长撰写结构清晰、读者友好的中文文章。

要求：
1. 标题控制在 15-25 字，包含关键词，吸引点击
2. 文章 800-1500 字
3. 使用 H2/H3 分级标题，结构清晰
4. 段落简短，每段不超过 4 行
5. 适当使用列表、引用、加粗等格式
6. 内容实用、有深度，不要堆砌废话
7. 用 HTML 格式输出（不要用 Markdown）
8. 不要在开头写"标题："这种标签

输出格式（严格遵守）：
第一行是标题（纯文本，不要带 # 符号）
空一行
然后是 HTML 格式的文章正文"""

    user_prompt = f"""请围绕主题「{topic}」写一篇高质量的 SEO 博客文章。

要求：
- 目标读者：对主题感兴趣的一般用户
- 语气：专业但平易近人
- 包含：背景介绍、核心要点、实用建议、总结
- 字数：1000-1500 字
- 输出 HTML 格式（用 <h2>、<h3>、<p>、<ul>、<li>、<strong> 等标签）"""

    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
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
        log(f"✅ AI 生成成功，字符数: {len(content)}")

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
        log("❌ AI 生成超时（>120秒）")
        sys.exit(1)
    except Exception as e:
        log(f"❌ AI 生成失败: {e}")
        if hasattr(e, "response") and e.response is not None:
            log(f"   响应内容: {e.response.text[:500]}")
        sys.exit(1)


def post_to_wordpress(title: str, content: str, topic: str) -> dict:
    """通过 WordPress REST API 发布文章"""
    log(f"📝 准备发布到 WordPress: {title}")

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
            auth=(WP_USERNAME, WP_APP_PASSWORD),
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
        post = resp.json()
        log(f"✅ 发布成功！文章 ID: {post.get('id')}")
        log(f"   状态: {post.get('status')}")
        log(f"   链接: {post.get('link')}")
        return post
    except requests.exceptions.HTTPError as e:
        log(f"❌ WordPress 发布失败: {e.response.status_code}")
        log(f"   响应: {e.response.text[:500]}")
        sys.exit(1)
    except Exception as e:
        log(f"❌ WordPress 发布失败: {e}")
        sys.exit(1)


def main() -> None:
    log("=" * 50)
    log("🚀 WordPress 自动发文脚本启动")

    # 1. 检查环境
    check_env()

    # 2. 加载主题
    topics = load_topics()

    # 3. 选择主题
    state = load_state()
    topic = pick_topic(topics, state)
    log(f"🎯 本次主题: {topic}")

    # 4. 生成文章
    article = generate_article(topic)
    log(f"📄 标题: {article['title']}")

    # 5. 发布到 WordPress
    post = post_to_wordpress(article["title"], article["content"], topic)

    # 6. 保存状态
    save_state(state)

    log("=" * 50)
    log("🎉 全部完成！")
    log(f"   文章 ID: {post.get('id')}")
    log(f"   状态: {post.get('status')}")


if __name__ == "__main__":
    main()
