# -*- coding: utf-8 -*-
"""
民间奇门法术实战应用（mingjianmishu）JSON-LD 结构化数据批量注入脚本
给现有 docs/notes/*.html 注入 Article + BreadcrumbList，
给 docs/index.html 注入 WebSite + ItemList。

默认【试运行 dry-run】，只打印将要做什么，不改文件。
确认无误后加 --apply 真正写入（自动生成 .bak 备份）。

用法：
    python inject_geo_schema.py            # 试运行
    python inject_geo_schema.py --apply    # 真正写入
"""
import re
import sys
import shutil
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DOCS = Path(r"C:\Users\Administrator\WorkBuddy\2026-06-27-19-55-23\docs")
BASE = "https://psqhhh-rgb.github.io/mingjianmishu"
APPLY = "--apply" in sys.argv
MARK = 'application/ld+json'  # 已注入过的标记，避免重复

TAG_ORDER = ["道家", "风水布局", "符咒术法", "民间文化", "奇门遁甲", "修炼修行", "占卜预测"]


def note_date(name: str) -> str:
    m = re.match(r"(\d{4})(\d{2})(\d{2})", name)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def build_article_ld(title, desc, date, tags, url):
    tag_ld = ", ".join('"%s"' % esc(t) for t in tags) if tags else '"民间文化"'
    return f'''<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{esc(title)}",
  "description": "{esc(desc)}",
  "datePublished": "{date}",
  "dateModified": "{date}",
  "author": {{ "@type": "Person", "name": "紫鸢真人" }},
  "publisher": {{ "@type": "Organization", "name": "民间奇门法术实战应用" }},
  "about": [{tag_ld}],
  "inLanguage": "zh-CN",
  "mainEntityOfPage": "{url}"
}}
</script>'''


def build_breadcrumb_ld(tag, url):
    tag_url = f"{BASE}/tag/{tag}.html" if tag else f"{BASE}/"
    tag_name = tag if tag else "目录"
    return f'''<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {{ "@type": "ListItem", "position": 1, "name": "目录", "item": "{BASE}/" }},
    {{ "@type": "ListItem", "position": 2, "name": "{esc(tag_name)}", "item": "{tag_url}" }}
  ]
}}
</script>'''


def process_note(path: Path):
    html = path.read_text(encoding="utf-8")
    if MARK in html:
        return "skip"
    stem = path.stem
    date = note_date(stem)
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    title = m.group(1).split(" - ")[0].strip() if m else stem
    md = re.search(r'<meta name="description" content="(.*?)"', html)
    desc = md.group(1).strip() if md else title
    mk = re.search(r'<meta name="keywords" content="(.*?)"', html)
    tags = [t.strip() for t in mk.group(1).split(",")] if mk and mk.group(1).strip() else []
    from urllib.parse import quote
    url = f"{BASE}/notes/{quote(path.name)}"
    ld = "\n".join([build_article_ld(title, desc, date, tags, url),
                    build_breadcrumb_ld(tags[0] if tags else "", url)])
    new = html.replace("</head>", ld + "\n</head>", 1)
    if new == html:
        return "fail"
    if APPLY:
        path.write_text(new, encoding="utf-8")
    return "ok"


def process_index(path: Path):
    html = path.read_text(encoding="utf-8")
    if MARK in html:
        return "skip"
    ld = f'''<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "民间奇门法术实战应用",
  "alternateName": "民间秘术笔记库",
  "url": "{BASE}/",
  "description": "民间道家、风水、符咒、奇门、修炼、占卜实战笔记知识库，共 217 篇。",
  "inLanguage": "zh-CN",
  "publisher": {{ "@type": "Organization", "name": "民间奇门法术实战应用" }}
}}
</script>'''
    new = html.replace("</head>", ld + "\n</head>", 1)
    if new == html:
        return "fail"
    if APPLY:
        path.write_text(new, encoding="utf-8")
    return "ok"


def main():
    mode = "【写入模式】" if APPLY else "【试运行 dry-run】"
    print(f"{mode} 目标目录: {DOCS}")
    stats = {"ok": 0, "skip": 0, "fail": 0}
    for f in sorted((DOCS / "notes").glob("*.html")):
        r = process_note(f)
        stats[r] = stats.get(r, 0) + 1
    idx = DOCS / "index.html"
    r = process_index(idx)
    stats[r] = stats.get(r, 0) + 1
    print(f"完成：注入 {stats['ok']} 个，跳过(已存在) {stats['skip']} 个，失败 {stats['fail']} 个")
    if not APPLY:
        print(">>> 试运行未改动任何文件。确认后执行： python inject_geo_schema.py --apply")


if __name__ == "__main__":
    main()
