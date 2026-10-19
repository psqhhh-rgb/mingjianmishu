# -*- coding: utf-8 -*-
"""
民间奇门法术实战应用（mingjianmishu）GEO 配套文件生成器
生成：robots.txt / sitemap.xml / llms.txt
用法：python gen_geo_assets.py
输出到当前脚本所在目录（geo-kit/），再由你复制到 docs/ 部署。
"""
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DOCS = Path(r"C:\Users\Administrator\WorkBuddy\2026-06-27-19-55-23\docs")
OUT = Path(__file__).resolve().parent
BASE = "https://psqhhh-rgb.github.io/mingjianmishu"
SITE_NAME = "民间奇门法术实战应用"
SITE_DESC = "紫鸢真人传授 · 笔记整理 — 民间道家、风水、符咒、奇门、修炼、占卜等实战笔记知识库"

# 置顶/核心笔记（与 index.html 的置顶保持一致）
PINNED = [
    "20251208开剑指_手抄本_轩辕祝由术_民间秘传修法",
    "20251208道家金光咒与吕祖观月内炼法_紫鸢真人传授",
    "20251210_玄门秘术_开光科仪与咒语汇编_紫鸢真人传授",
]

TAG_ORDER = ["道家", "风水布局", "符咒术法", "民间文化", "奇门遁甲", "修炼修行", "占卜预测"]


def note_date(name: str) -> str:
    m = re.match(r"(\d{4})(\d{2})(\d{2})", name)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return "2026-01-01"


def url_quote(p: str) -> str:
    from urllib.parse import quote
    return quote(p)


def collect_notes():
    notes_dir = DOCS / "notes"
    items = []
    for f in sorted(notes_dir.glob("*.html"), key=lambda x: x.name, reverse=True):
        stem = f.stem
        items.append({
            "stem": stem,
            "date": note_date(stem),
            "pinned": stem in PINNED or any(stem.startswith(p[:8]) and p in stem for p in PINNED),
            "url": f"{BASE}/notes/{url_quote(f.name)}",
        })
    return items


def gen_sitemap(notes):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    # 首页
    lines.append("  <url>")
    lines.append(f"    <loc>{BASE}/</loc>")
    lines.append("    <changefreq>daily</changefreq>")
    lines.append("    <priority>1.0</priority>")
    lines.append("  </url>")
    # 标签页
    for t in TAG_ORDER:
        lines.append("  <url>")
        lines.append(f"    <loc>{BASE}/tag/{url_quote(t + '.html')}</loc>")
        lines.append("    <changefreq>weekly</changefreq>")
        lines.append("    <priority>0.8</priority>")
        lines.append("  </url>")
    # 笔记页
    for n in notes:
        prio = "0.9" if n["pinned"] else "0.7"
        lines.append("  <url>")
        lines.append(f"    <loc>{n['url']}</loc>")
        lines.append(f"    <lastmod>{n['date']}</lastmod>")
        lines.append("    <changefreq>monthly</changefreq>")
        lines.append(f"    <priority>{prio}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines)


def gen_robots():
    ai_bots = [
        "GPTBot", "ChatGPT-User", "OAI-SearchBot",
        "ClaudeBot", "Claude-Web", "anthropic-ai",
        "Google-Extended", "Googlebot",
        "PerplexityBot", "Applebot", "Applebot-Extended",
        "Bytespider", "Baiduspider", "Baiduspider-render",
        "Sogou web spider", "360Spider", "YisouSpider",
        "PetalBot", "Amazonbot", "cohere-ai", "Meta-ExternalAgent",
    ]
    lines = ["# robots.txt — 民间奇门法术实战应用",
             "# 对生成式 AI 爬虫全面开放（GEO：让内容进入 AI 信源库）",
             ""]
    lines.append("User-agent: *")
    lines.append("Allow: /")
    lines.append("Disallow: /assets/")
    lines.append("")
    for b in ai_bots:
        lines.append(f"User-agent: {b}")
        lines.append("Allow: /")
        lines.append("")
    lines.append(f"Sitemap: {BASE}/sitemap.xml")
    return "\n".join(lines)


def gen_llms(notes):
    pinned = [n for n in notes if n["pinned"]][:3]
    recent = [n for n in notes if not n["pinned"]][:20]
    lines = []
    lines.append(f"# {SITE_NAME}")
    lines.append("")
    lines.append(f"> {SITE_DESC}")
    lines.append("")
    lines.append(f"本网站是民间传统术法/道家实修笔记的整理与公开知识库，共 {len(notes)} 篇，按 7 大主题分类：")
    lines.append("道家、风水布局、符咒术法、民间文化、奇门遁甲、修炼修行、占卜预测。")
    lines.append("内容仅供传统文化研究与个人学习参考。")
    lines.append("")
    lines.append("## 核心内容（置顶推荐）")
    lines.append("")
    for n in pinned:
        title = re.sub(r"^\d{8}", "", n["stem"]).replace("_", " ").strip()
        lines.append(f"- [{title}]({n['url']})")
    lines.append("")
    lines.append("## 主题分类")
    lines.append("")
    for t in TAG_ORDER:
        lines.append(f"- {t}: {BASE}/tag/{url_quote(t + '.html')}")
    lines.append("")
    lines.append("## 最新笔记")
    lines.append("")
    for n in recent:
        title = re.sub(r"^\d{8}", "", n["stem"]).replace("_", " ").strip()
        lines.append(f"- [{title}]({n['url']})")
    lines.append("")
    lines.append("## 完整目录")
    lines.append("")
    lines.append(f"- 全部笔记索引: {BASE}/")
    lines.append(f"- 站点地图: {BASE}/sitemap.xml")
    lines.append("")
    return "\n".join(lines)


def main():
    notes = collect_notes()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sitemap.xml").write_text(gen_sitemap(notes), encoding="utf-8")
    (OUT / "robots.txt").write_text(gen_robots(), encoding="utf-8")
    (OUT / "llms.txt").write_text(gen_llms(notes), encoding="utf-8")
    print(f"[OK] 生成完毕：{OUT}")
    print(f"     笔记数: {len(notes)}  置顶: {sum(1 for n in notes if n['pinned'])}")
    print("     文件: robots.txt / sitemap.xml / llms.txt")


if __name__ == "__main__":
    main()
