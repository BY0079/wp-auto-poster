#!/usr/bin/env python3
"""一次性脚本：创建「关于」页面（page）"""
import os
import sys
import requests

WP_SITE_URL = os.environ.get("WP_SITE_URL", "").rstrip("/")
WP_USERNAME = os.environ.get("WP_USERNAME", "")
WP_USER_PWD = os.environ.get("WP_USER_PWD", "").replace(" ", "")

if not all([WP_SITE_URL, WP_USERNAME, WP_USER_PWD]):
    print("ERROR: Missing env vars (WP_SITE_URL / WP_USERNAME / WP_USER_PWD)")
    sys.exit(1)

CONTENT_HTML = """<div class="about-page" style="max-width: 760px; margin: 0 auto; font-size: 16px; line-height: 1.85; color: #333;">

<p style="text-align: center; font-size: 28px; font-weight: bold; margin: 0 0 8px 0; color: #222;">Hi，我是 seabell 👋</p>
<p style="text-align: center; font-size: 17px; color: #777; margin: 0 0 40px 0;">一个从零开始折腾建站的普通人</p>

<p>2026 年，我决定做一件想了很久的事：把折腾的过程记录下来，分享给和我一样「想建站但不知道从哪开始」的朋友。</p>

<p>于是有了这个博客 —— <strong style="color: #4a90e2;">「小白建站记」</strong>。</p>

<h2 style="margin: 40px 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid #4a90e2; color: #222;">为什么要建这个博客？</h2>

<p>最初只是想搭个个人主页，但真动手才发现：服务器怎么选？域名怎么备案？WordPress 怎么装？……每一个问题都能让我卡半天。</p>

<p>网上教程一大堆，但大部分要么太老、要么太技术、要么就是软广。我想要的，就是一个<strong>说人话、踩过的坑讲清楚</strong>的地方。</p>

<p>所以，我把自己每一次「从不会到会」的折腾都写下来 —— 你看到的每一篇文章，都是我<strong>真实走过的路</strong>。错了会承认，踩过的坑会提醒，看到的好处也会写。</p>

<h2 style="margin: 40px 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid #4a90e2; color: #222;">这里会写什么？</h2>

<p>主要分享这几类内容：</p>

<ul style="line-height: 2.1; padding-left: 20px;">
  <li>🚀 <strong>云服务器与建站</strong>：选什么配置、避哪些坑、域名备案、SSL 证书……</li>
  <li>🤖 <strong>AI 与效率</strong>：AI 工具怎么用才不交智商税</li>
  <li>📝 <strong>WordPress 建站</strong>：主题推荐、性能优化、SEO 实战</li>
  <li>💻 <strong>编程开发</strong>：新手友好的编程入门</li>
  <li>🌱 <strong>新手入门</strong>：从零开始的各种小教程</li>
  <li>🌐 <strong>数字生活</strong>：让生活更舒服的数字工具</li>
</ul>

<h2 style="margin: 40px 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid #4a90e2; color: #222;">关于 AI 辅助（必须坦白）</h2>

<p>我必须坦白：这里大部分文章会用 AI 辅助写作（我用了硅基流动的 DeepSeek 和 Qwen 模型），但<strong>所有选题、核心观点、踩坑经验都是我自己的</strong>。AI 帮我把思路理顺、把话写顺，但不会替我思考 —— 选什么写、不写什么、写到什么深度，这些都是我把关的。</p>

<p>这样做的好处是：<strong>我能保持稳定更新，质量也不会太拉跨</strong>。坏处坦白说也有：偶尔会有「AI 味」比较重的时候，遇到了欢迎指出。</p>

<h2 style="margin: 40px 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid #4a90e2; color: #222;">适合谁看？</h2>

<ul style="line-height: 2.1; padding-left: 20px;">
  <li>🌱 完全没建过站的小白</li>
  <li>🌿 建过站但踩过坑、想少走弯路的</li>
  <li>🚀 想用 AI 工具提升效率的同路人</li>
  <li>💡 对云服务器、AI、建站感兴趣的所有人</li>
</ul>

<h2 style="margin: 40px 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid #4a90e2; color: #222;">联系我</h2>

<p>如果你有任何问题、建议、或者只是想打个招呼：</p>

<ul style="line-height: 2.1; padding-left: 20px;">
  <li>📧 邮箱：l*****@qq.com</li>
  <li>💬 留言：每篇文章底部都有评论框</li>
</ul>

<h2 style="margin: 40px 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid #4a90e2; color: #222;">🤝 友链</h2>

<p>欢迎同路人交换友链。请发邮件到上面邮箱，附上：</p>

<ol style="line-height: 2.1; padding-left: 20px;">
  <li>你的博客地址</li>
  <li>博客名 + 一句话简介</li>
  <li>（可选）你的头像或 Logo</li>
</ol>

<h2 style="margin: 40px 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid #4a90e2; color: #222;">最后</h2>

<p>建站是一个漫长的折腾。希望这里的内容能帮你少走一些弯路，少交一些智商税。</p>

<p>如果你看完觉得「这哥们写得还挺实在」，那就是我最大的动力。</p>

<hr style="margin: 40px 0; border: none; border-top: 1px solid #eee;">

<p style="text-align: center; color: #888; font-style: italic; margin: 20px 0;">
最后：建站是一个漫长的折腾，希望这里的内容能帮你少走一些弯路。<br><br>
如果这个博客对你哪怕有一点帮助，就值了。<br><br>
<strong style="color: #4a90e2;">seabell</strong> · 于 2026 年 9 月<br>
折腾不停，笔耕不辍 ✍️
</p>

</div>"""

print(f"INFO: Creating About page...")
print(f"  Site: {WP_SITE_URL}")
print(f"  User: {WP_USERNAME}")

try:
    resp = requests.post(
        f"{WP_SITE_URL}/wp-json/wp/v2/pages",
        auth=(WP_USERNAME, WP_USER_PWD),
        json={
            "title": "关于",
            "content": CONTENT_HTML,
            "status": "publish",
            "slug": "about",
        },
        timeout=30,
    )
    print(f"DEBUG: HTTP Status = {resp.status_code}")

    text = resp.text.strip()
    json_start = text.find("{")
    json_end = text.rfind("}") + 1
    if resp.status_code == 201 and json_start >= 0:
        page = __import__('json').loads(text[json_start:json_end])
        print(f"OK: Page created!")
        print(f"  ID: {page.get('id')}")
        print(f"  Slug: {page.get('slug')}")
        print(f"  Link: {page.get('link')}")
        print(f"  Status: {page.get('status')}")
    else:
        print(f"ERROR: {resp.text[:500]}")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)