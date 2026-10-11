#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Obsidian Notes → Static HTML Site Converter
将 Obsidian 笔记文件夹转换为可部署到 GitHub Pages 的静态网站。
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import re
import shutil
import html
import markdown
from pathlib import Path
from datetime import datetime

# ============ 配置 ============
NOTES_DIR = Path(r"E:\psqhhh\民间奇门法术实战应用")
MEDIA_DIR = Path(r"E:\psqhhh")  # 图片视频所在目录
OUTPUT_DIR = Path(r"C:\Users\Administrator\WorkBuddy\2026-06-27-19-55-23\docs")
ASSETS_DIR = OUTPUT_DIR / "assets"
PAGES_DIR = OUTPUT_DIR / "notes"
# 编者整理文章目录（与笔记同名，键为源笔记 stem）：editorial/<stem>.md
EDITORIAL_DIR = Path(r"C:\Users\Administrator\WorkBuddy\2026-06-27-19-55-23\editorial")

SITE_TITLE = "民间奇门法术实战应用"
SITE_SUBTITLE = "紫鸢真人传授 · 笔记整理"

# ============ 模板 ============
PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - {site_title}</title>
<meta name="description" content="{desc}">
<meta name="keywords" content="{tags}">
<meta property="og:title" content="{title}">
<meta property="og:site_name" content="{site_title}">
<meta property="og:type" content="article">
<link rel="stylesheet" href="../style.css">
<link rel="preconnect" href="https://fonts.googleapis.com">
</head>
<body>
<nav class="topbar">
  <a href="../index.html" class="back-link">← 返回目录</a>
  <span class="site-name">{site_title}</span>
</nav>
<main class="article">
  <article>
    <h1 class="article-title">{title}</h1>
    <div class="article-meta">{meta}</div>
    {tags_html}
    {content}
  </article>
</main>
</body>
</html>"""

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{site_title}</title>
<meta name="description" content="{site_desc}">
<meta name="keywords" content="道家,风水布局,符咒术法,民间文化,奇门遁甲,修炼修行,占卜预测">
<meta property="og:title" content="{site_title}">
<meta property="og:description" content="{site_desc}">
<meta property="og:type" content="website">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="hero">
  <h1>{site_title}</h1>
  <p class="subtitle">{site_subtitle}</p>
  <div class="search-box">
    <input type="text" id="searchInput" placeholder="搜索笔记标题..." autocomplete="off">
  </div>
  <div class="stats">共 {count} 篇笔记</div>
  <div class="tag-filter-bar">
    {tag_buttons}
  </div>
</header>
<main class="notes-grid">
{cards}
</main>
<footer class="footer">
  <p>由 Obsidian 笔记自动生成 · {generated}</p>
</footer>
<script>
const searchInput = document.getElementById('searchInput');
let activeTags = null;
searchInput.addEventListener('input', function() {{
  const q = this.value.toLowerCase().trim();
  document.querySelectorAll('.note-card').forEach(card => {{
    const title = card.dataset.title.toLowerCase();
    const tags = (card.dataset.tags || '').split('|');
    const matchSearch = !q || title.includes(q);
    const matchTags = !activeTags || tags.some(t => activeTags.includes(t.trim()));
    card.style.display = (matchSearch && matchTags) ? '' : 'none';
  }});
}});
function toggleTag(tagName) {{
  if (!activeTags) activeTags = [];
  const idx = activeTags.indexOf(tagName);
  if (idx > -1) activeTags.splice(idx, 1);
  else activeTags.push(tagName);
  if (activeTags.length === 0) activeTags = null;
  // refresh
  searchInput.dispatchEvent(new Event('input'));
}}
</script>
</body>
</html>"""

CARD_TEMPLATE = """<a class="note-card" href="notes/{filename}" data-title="{title_escaped}" data-tags="{tags}">
  <div class="card-body">
    <div class="card-title">{title}</div>
    <div class="card-date">{date}</div>
  </div>
</a>"""

TAG_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{tag} - {site_title}</title>
<meta name="description" content="{tag} — {site_title}中的{count}篇笔记">
<meta name="keywords" content="{tag},{site_keywords}">
<meta property="og:title" content="{tag}">
<meta property="og:type" content="website">
<link rel="stylesheet" href="../style.css">
</head>
<body>
<nav class="topbar">
  <a href="../index.html" class="back-link">← 返回首页</a>
  <span class="site-name">{tag} · {count} 篇</span>
</nav>
<main class="article">
  <h1 class="article-title">{tag}</h1>
  <div class="article-meta">{site_title}</div>
  <div class="tag-notes-list">
{notes}
  </div>
</main>
<footer class="footer">
  <p><a href="../index.html" style="color:var(--accent)">← 返回首页</a></p>
  <p>由 Obsidian 笔记自动生成 · {generated}</p>
</footer>
</body>
</html>"""

CSS = """*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#f8f6f1;--card:#fffdf8;--text:#2c2418;--muted:#8a7c6a;
  --accent:#8b6914;--border:#e0d8c8;--shadow:rgba(139,105,20,.08);
}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",sans-serif;
  background:var(--bg);color:var(--text);line-height:1.8}

/* Hero */
.hero{text-align:center;padding:3rem 1.5rem 2rem;background:linear-gradient(135deg,#f5efe0,#ebe3d0)}
.hero h1{font-size:2rem;color:var(--accent);letter-spacing:.05em;margin-bottom:.3rem}
.subtitle{color:var(--muted);font-size:.95rem}
.search-box{margin:1.5rem auto;max-width:400px}
.search-box input{width:100%;padding:.7rem 1.2rem;border:2px solid var(--border);
  border-radius:2rem;font-size:.95rem;background:var(--card);color:var(--text);
  transition:border-color .2s}
.search-box input:focus{outline:none;border-color:var(--accent)}
.stats{color:var(--muted);font-size:.8rem}

/* Notes grid */
.notes-grid{max-width:900px;margin:2rem auto;padding:0 1rem;
  display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1rem}
.note-card{display:block;text-decoration:none;color:inherit;
  background:var(--card);border:1px solid var(--border);border-radius:.5rem;
  padding:1.2rem;transition:all .2s;position:relative;overflow:hidden}
.note-card:hover{transform:translateY(-2px);box-shadow:0 6px 20px var(--shadow);
  border-color:var(--accent)}
.card-body{display:flex;flex-direction:column;gap:.5rem}
.card-title{font-size:.95rem;font-weight:600;color:var(--text);
  display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.card-date{font-size:.75rem;color:var(--muted)}

/* Article page */
.topbar{display:flex;align-items:center;gap:1rem;padding:.8rem 1.5rem;
  background:var(--card);border-bottom:1px solid var(--border);
  position:sticky;top:0;z-index:10}
.back-link{color:var(--accent);text-decoration:none;font-size:.85rem;white-space:nowrap}
.back-link:hover{text-decoration:underline}
.site-name{color:var(--muted);font-size:.85rem}

.article{max-width:720px;margin:0 auto;padding:2rem 1.5rem 4rem}
.article-title{font-size:1.6rem;color:var(--accent);margin-bottom:.5rem;line-height:1.4}
.article-meta{color:var(--muted);font-size:.8rem;margin-bottom:2rem;
  padding-bottom:1rem;border-bottom:1px solid var(--border)}
.article p{margin-bottom:1rem}
.article h2{font-size:1.3rem;color:var(--text);margin:2rem 0 .8rem}
.article h3{font-size:1.1rem;color:var(--text);margin:1.5rem 0 .5rem}
.article img{max-width:100%;border-radius:.5rem;margin:1rem 0;
  box-shadow:0 2px 12px var(--shadow)}
.article video{max-width:100%;border-radius:.5rem;margin:1rem 0}
.article a{color:var(--accent)}
.article ul,.article ol{margin:1rem 0 1rem 1.5rem}
.article li{margin-bottom:.3rem}
.article-blockquote{border-left:3px solid var(--accent);padding-left:1rem;
  margin:1rem 0;color:var(--muted)}
.article-blockcode{background:var(--border);padding:.1rem .3rem;border-radius:.2rem;font-size:.9em}
.article-pre{background:#2c2418;color:#f0e8d8;padding:1rem;border-radius:.5rem;
  overflow-x:auto;margin:1rem 0}
.article-pre code{background:none;padding:0}
.article table{width:100%;border-collapse:collapse;margin:1rem 0}
.article th,.article td{border:1px solid var(--border);padding:.5rem .8rem;text-align:left}
.article th{background:var(--card)}
.tags-bar{display:flex;gap:.4rem;flex-wrap:wrap;margin:1rem 0 1.5rem}
.tag{display:inline-block;padding:.15rem .6rem;background:var(--accent);
  color:#fff;border-radius:2rem;font-size:.75rem;font-weight:500;
  text-decoration:none;transition:opacity .2s}
.tag:hover{opacity:.8}
.tag-filter-bar{margin:1rem auto;display:flex;gap:.5rem;justify-content:center;flex-wrap:wrap}
.tag-filter-btn{display:inline-block;padding:.25rem .8rem;background:var(--card);
  color:var(--text);border:1px solid var(--border);border-radius:2rem;
  font-size:.8rem;text-decoration:none;transition:all .2s}
.tag-filter-btn:hover,.tag-filter-btn.active{background:var(--accent);
  color:#fff;border-color:var(--accent)}
.tag-note-item{display:block;text-decoration:none;color:inherit;
  background:var(--card);border:1px solid var(--border);border-radius:.5rem;
  padding:1rem 1.2rem;margin-bottom:.5rem;transition:all .2s}
.tag-note-item:hover{transform:translateY(-1px);box-shadow:0 4px 12px var(--shadow);
  border-color:var(--accent)}
.tag-note-item .tn-title{font-size:.9rem;font-weight:600;color:var(--text);margin-bottom:.2rem}
.tag-note-item .tn-date{font-size:.75rem;color:var(--muted)}

.footer{text-align:center;padding:2rem;color:var(--muted);font-size:.8rem}

/* ===== 编者整理文章（样板体例）===== */
.part-label{display:inline-flex;align-items:center;gap:.5rem;font-size:.82rem;font-weight:600;
  letter-spacing:.05em;color:#fff;background:#8a7c6a;border-radius:2rem;padding:.3rem 1rem;margin-bottom:1.2rem}
.part-label--editor{background:linear-gradient(135deg,#8b6914,#a98424)}
.raw-note{background:var(--bg);border:1px dashed var(--border);border-radius:.6rem;padding:1.2rem 1.3rem}
.raw-note p{color:#4a4133;font-size:.95rem;margin-bottom:.8rem}
.raw-note p:last-child{margin-bottom:0}
.divider-note{display:flex;align-items:center;gap:.8rem;margin:2.5rem 0 1.8rem;
  color:var(--muted);font-size:.8rem;letter-spacing:.1em}
.divider-note::before,.divider-note::after{content:"";flex:1;height:1px;background:var(--border)}
.editorial{background:var(--card);border:1px solid var(--border);border-radius:.8rem;
  padding:1.6rem 1.6rem 1.2rem;box-shadow:0 4px 20px var(--shadow)}
.editorial h2{border-bottom:2px solid var(--accent);padding-bottom:.4rem;
  color:var(--accent);font-size:1.25rem;margin:1.8rem 0 .8rem}
.editorial .ed-title{border:none;color:var(--text);font-size:1.4rem;margin:.2rem 0 1rem;padding:0}
.tldr{background:#faf6ea;border-left:4px solid var(--accent);border-radius:.4rem;
  padding:.9rem 1.1rem;margin:0 0 1.5rem;font-size:.92rem;color:#5c4f38}
.related{margin-top:1.5rem;padding-top:1rem;border-top:1px dashed var(--border);
  font-size:.85rem;color:var(--muted);line-height:1.9}
.related a{color:var(--accent);text-decoration:none}
.related a:hover{text-decoration:underline}
.disclaimer{margin-top:1.5rem;font-size:.78rem;color:var(--muted);background:var(--bg);
  border:1px solid var(--border);border-radius:.5rem;padding:.9rem 1.1rem;line-height:1.7}

@media(max-width:600px){
  .hero{padding:2rem 1rem 1.5rem}
  .hero h1{font-size:1.5rem}
  .notes-grid{grid-template-columns:1fr}
  .article{padding:1.5rem 1rem 3rem}
}"""


def parse_date_from_filename(filename: str) -> str:
    """从文件名中提取日期，如 20260523xxx → 2026-05-23"""
    m = re.match(r'(\d{4})(\d{2})(\d{2})', filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ""


def slugify(filename: str) -> str:
    """将文件名/笔记名转为 URL 安全的 HTML 文件名。
    只剥离末尾的 .md 扩展名（不能用 Path.stem——笔记名里可能含 '888.88' 这类点号，
    那样会被错误地截断，导致 related 链接指向不存在的文件）。"""
    name = Path(filename).name
    if name.lower().endswith(".md"):
        name = name[:-3]
    safe = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', name)
    return safe + ".html"


def convert_obsidian_embeds(content: str) -> str:
    """将 Obsidian ![[file]] 语法转为标准 markdown"""
    def replace_embed(match):
        filename = match.group(1).strip()
        ext = Path(filename).suffix.lower()

        if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'):
            return f'![{filename}](../assets/{filename})'
        elif ext in ('.mp4', '.webm', '.mov', '.avi', '.mkv'):
            return f'<video controls><source src="../assets/{filename}" type="video/mp4">您的浏览器不支持视频播放。</video>'
        elif ext in ('.mp3', '.wav', '.ogg', '.m4a'):
            return f'<audio controls><source src="../assets/{filename}" type="audio/mpeg">您的浏览器不支持音频播放。</audio>'
        else:
            return f'[{filename}](../assets/{filename})'

    # 匹配 ![[文件名]] 或 ![[文件名|别名]]
    content = re.sub(r'!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]', replace_embed, content)
    return content


def convert_obsidian_links(content: str) -> str:
    """将 Obsidian [[笔记名]] 内部链接转为链接（目前无内部链接，预留）"""
    def replace_link(match):
        note_name = match.group(1).strip()
        slug = slugify(note_name)
        return f'[{note_name}](./{slug})'

    content = re.sub(r'(?<!\!)\[\[([^\]]+)\]\]', replace_link, content)
    return content


# ============ SEO Tags 配置 ============
ALL_TAGS = [
    "道家", "风水布局", "符咒术法",
    "民间文化", "奇门遁甲", "修炼修行", "占卜预测"
]

TAG_KEYWORDS = {
    "道家": ["道家", "道法", "吕祖", "金光咒", "道教", "道人", "道门", "太上"],
    "风水布局": ["风水", "阳宅", "阴宅", "财位", "煞气", "罗盘", "峦头", "理气",
                 "八宅", "玄空", "太岁", "化解", "布局", "罗经", "龙脉", "藏风",
                 "得水", "明堂", "案山", "朝山", "土公", "地师"],
    "符咒术法": ["符咒", "符字", "禁咒", "祝由", "咒语", "开光", "施食", "变亿",
                 "摄召", "召将", "师刀", "罡", "诀", "印", "法事", "法坛", "法器",
                 "护法", "童子", "降妖", "伏魔", "驱邪", "镇宅", "安太岁"],
    "民间文化": ["民间", "偏方", "土方", "习俗", "祭祀", "祖先", "香火", "庙会",
                 "拜神", "还愿", "许愿", "供桌", "神龛", "土地公", "灶王",
                 "财神", "关帝", "观音", "妈祖", "王爷", "保生大帝"],
    "奇门遁甲": ["奇门", "遁甲", "九宫", "八门", "九星", "八神", "天干", "地支",
                 "排盘", "拆补", "置闰", "值符", "值使", "天盘", "地盘", "隐干",
                 "击刑", "入墓", "马星", "空亡", "旬首", "时家", "日家", "年家"],
    "修炼修行": ["修炼", "打坐", "站桩", "辟谷", "静坐", "冥想", "入定", "出神",
                 "内炼", "外练", "气功", "导引", "吐纳", "周天", "丹田", "经脉",
                 "炼精化气", "炼气化神", "炼神还虚", "炼虚合道", "三宝", "精气神",
                 "元神", "识神", "性功", "命功", "双修", "采补", "导引", "服食"],
    "占卜预测": ["占卜", "预测", "算命", "八字", "流年", "大运", "趋吉避凶", "六爻",
                 "梅花", "太乙", "小六壬", "铁板", "紫微", "面相", "手相", "测字",
                 "起名", "择日", "合婚", "摇卦", "抽签", "问卦", "起课"]
}


def select_tags(title: str, content: str) -> list:
    """根据标题和内容，从关键词匹配中选择1-3个tag"""
    text = title + content
    scored = {}
    for tag, keywords in TAG_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scored[tag] = score
    # 取得分最高的最多3个
    sorted_tags = sorted(scored.items(), key=lambda x: (-x[1], x[0]))
    return [t[0] for t in sorted_tags[:3]]


# ============ SEO Tags 配置 ============
ALL_TAGS = [
    "道家", "风水布局", "符咒术法",
    "民间文化", "奇门遁甲", "修炼修行", "占卜预测"
]

TAG_KEYWORDS = {
    "道家": ["道家", "道法", "吕祖", "金光咒", "道教", "道人", "道门", "太上"],
    "风水布局": ["风水", "阳宅", "阴宅", "财位", "煞气", "罗盘", "峦头", "理气",
                 "八宅", "玄空", "太岁", "化解", "布局", "罗经", "龙脉", "藏风",
                 "得水", "明堂", "案山", "朝山", "土公", "地师"],
    "符咒术法": ["符咒", "符字", "禁咒", "祝由", "咒语", "开光", "施食", "变亿",
                 "摄召", "召将", "师刀", "罡", "诀", "印", "法事", "法坛", "法器",
                 "护法", "童子", "降妖", "伏魔", "驱邪", "镇宅", "安太岁"],
    "民间文化": ["民间", "偏方", "土方", "习俗", "祭祀", "祖先", "香火", "庙会",
                 "拜神", "还愿", "许愿", "供桌", "神龛", "土地公", "灶王",
                 "财神", "关帝", "观音", "妈祖", "王爷", "保生大帝"],
    "奇门遁甲": ["奇门", "遁甲", "九宫", "八门", "九星", "八神", "天干", "地支",
                 "排盘", "拆补", "置闰", "值符", "值使", "天盘", "地盘", "隐干",
                 "击刑", "入墓", "马星", "空亡", "旬首", "时家", "日家", "年家"],
    "修炼修行": ["修炼", "打坐", "站桩", "辟谷", "静坐", "冥想", "入定", "出神",
                 "内炼", "外练", "气功", "导引", "吐纳", "周天", "丹田", "经脉",
                 "炼精化气", "炼气化神", "炼神还虚", "炼虚合道", "三宝", "精气神",
                 "元神", "识神", "性功", "命功", "双修", "采补", "导引", "服食"],
    "占卜预测": ["占卜", "预测", "算命", "八字", "流年", "大运", "趋吉避凶", "六爻",
                 "梅花", "太乙", "小六壬", "铁板", "紫微", "面相", "手相", "测字",
                 "起名", "择日", "合婚", "摇卦", "抽签", "问卦", "起课"]
}


def select_tags(title: str, content: str) -> list:
    """根据标题和内容，从关键词匹配中选择1-3个tag"""
    text = title + content
    scored = {}
    for tag, keywords in TAG_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scored[tag] = score
    # 取得分最高的最多3个
    sorted_tags = sorted(scored.items(), key=lambda x: (-x[1], x[0]))
    return [t[0] for t in sorted_tags[:3]]


def process_markdown(content: str) -> tuple:
    """处理 markdown 内容，返回 (html_content, referenced_media)"""
    referenced = set()

    # 提取引用的媒体文件
    for m in re.finditer(r'!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]', content):
        referenced.add(m.group(1).strip())

    # 转换 Obsidian 语法
    content = convert_obsidian_embeds(content)
    content = convert_obsidian_links(content)

    # Markdown → HTML
    md = markdown.Markdown(extensions=['extra', 'nl2br', 'sane_lists', 'toc'])
    html_content = md.convert(content)

    return html_content, referenced


# ============ 编者整理文章（editorial）============
EDITORIAL_DISCLAIMER = (
    '<div class="disclaimer"><strong>说明与免责：</strong>'
    '本站为民间修炼、民俗文化与传统文化资料的整理与记录，内容源自传承者口传与个人修习体会，'
    '仅供文化交流与研究参考，<strong>不构成医疗、健康、投资或任何功效承诺</strong>。'
    '所述内容属传统术数范畴，请理性看待；如身体不适，请及时就医。请遵守法律法规与公序良俗。</div>'
)


def load_editorial(stem: str):
    """读取同名编者整理文章（editorial/<stem>.md），返回 (meta, body) 或 None。
    front matter 支持字段：title / tldr / related（用 | 分隔）。"""
    path = EDITORIAL_DIR / f"{stem}.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    meta = {}
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm = text[3:end].strip()
            body = text[end + 4:].strip()
            for line in fm.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
    return meta, body


def render_editorial(stem: str) -> str:
    """将编者整理文章渲染为 HTML 区块；没有则返回空串。"""
    data = load_editorial(stem)
    if not data:
        return ""
    meta, body = data
    md = markdown.Markdown(extensions=["extra", "sane_lists"])
    body_html = md.convert(body)
    title = meta.get("title", "")
    tldr = meta.get("tldr", "")
    related = [r.strip() for r in meta.get("related", "").split("|") if r.strip()]

    parts = ['<div class="divider-note">以下为编者整理的主题文章</div>',
             '<span class="part-label part-label--editor">编者整理 · 主题文章</span>',
             '<div class="editorial">']
    if title:
        parts.append(f'<h2 class="ed-title">{html.escape(title)}</h2>')
    if tldr:
        parts.append(f'<div class="tldr"><strong>一句话结论：</strong>{html.escape(tldr)}</div>')
    parts.append(body_html)
    if related:
        links = " · ".join(
            f'<a href="./{slugify(r)}">{html.escape(r)}</a>' for r in related
        )
        parts.append(f'<div class="related"><strong>本页主题整合自以下原始记录：</strong>{links}</div>')
    parts.append(EDITORIAL_DISCLAIMER)
    parts.append("</div>")
    return "\n".join(parts)


def wrap_note_content(stem: str, html_content: str) -> str:
    """若有编者整理文章，则在原始对话内容外加"原始对话记录"标签，并在其后追加文章；否则原样返回。"""
    editorial_html = render_editorial(stem)
    if not editorial_html:
        return html_content
    return (
        '<span class="part-label">原始对话记录</span>\n'
        f'<div class="raw-note">{html_content}</div>\n'
        + editorial_html
    )


def auto_split_large_file(md_file: Path) -> list:
    """自动检测并拆分大于 25MB 的文件，返回拆分后的文件列表"""
    size = md_file.stat().st_size
    size_mb = size / (1024 * 1024)
    
    if size_mb <= 25:
        return [md_file]
    
    print(f"\n  ⚠ 检测到大文件: {md_file.name} ({size_mb:.1f} MB)，自动拆分...")
    
    # 读取文件内容
    content = md_file.read_text(encoding='utf-8')
    
    # 查找所有图片嵌入位置
    matches = list(re.finditer(r'!\[[^\]]*\]\(data:image', content))
    
    if not matches:
        # 没有图片，按文本行数平分
        mid = len(content) // 2
        part1 = content[:mid]
        part2 = content[mid:]
    else:
        # 按图片位置拆分(前一半图片在上一篇，后一半在下一篇)
        mid_idx = len(matches) // 2
        split_point = matches[mid_idx].start()
        part1 = content[:split_point]
        part2 = content[split_point:]
    
    # 生成拆分文件名
    stem = md_file.stem
    suffix = md_file.suffix
    part1_file = md_file.parent / f"{stem}（上）{suffix}"
    part2_file = md_file.parent / f"{stem}（下）{suffix}"
    
    # 写入拆分文件
    part1_file.write_text(part1, encoding='utf-8')
    part2_file.write_text(part2, encoding='utf-8')
    
    # 计算拆分后文件大小
    size1 = part1_file.stat().st_size / (1024 * 1024)
    size2 = part2_file.stat().st_size / (1024 * 1024)
    print(f"  拆分完成: 上篇 {size1:.1f} MB, 下篇 {size2:.1f} MB")
    
    # 删除原文件
    md_file.unlink()
    print(f"  已删除原文件: {md_file.name}")
    
    return [part1_file, part2_file]


def main():
    print("=" * 60)
    print("Obsidian → 静态网站转换器")
    print("=" * 60)

    # 清理输出目录
    if OUTPUT_DIR.exists():
        os.system(f'rm -rf "{OUTPUT_DIR}"')
    OUTPUT_DIR.mkdir(parents=True)
    ASSETS_DIR.mkdir()
    PAGES_DIR.mkdir()

    # 置顶推荐笔记
    PINNED_NOTES = [
        "20251210【玄门秘术】开光科仪与咒语汇编 紫鸢真人传授.md",
        "20251208道家金光咒与吕祖观月内炼法 紫鸢真人传授.md",
        "20251208开剑指，手抄本 轩辕祝由术，民间秘传修法.md",
    ]
    pinned_set = set(PINNED_NOTES)
    
    # 收集所有 markdown 文件（排除置顶笔记，置顶笔记单独处理）
    md_files = sorted(NOTES_DIR.glob("*.md"), key=lambda f: f.name, reverse=True)
    md_files = [f for f in md_files if f.name not in pinned_set]

    # 仅转换带日期的笔记（文件名以 YYYYMMDD 开头），跳过无日期的重复副本与空笔记
    before = len(md_files)
    md_files = [f for f in md_files if parse_date_from_filename(f.name) and f.stat().st_size > 0]
    skipped = before - len(md_files)
    if skipped:
        print(f"  已跳过 {skipped} 篇（无日期的重复副本 / 空笔记）")

    print(f"\n找到 {len(md_files)} 篇笔记（不含 {len(PINNED_NOTES)} 篇置顶）")

    all_referenced_media = set()
    cards_html = []

    # ========== 先处理置顶笔记，放在最前面 ==========
    for pinned_md in PINNED_NOTES:
        pinned_file = NOTES_DIR / pinned_md
        if not pinned_file.exists():
            print(f"  ⚠ 置顶文件不存在: {pinned_md}")
            continue
        title = pinned_file.stem
        date_str = parse_date_from_filename(pinned_file.name)
        html_filename = slugify(pinned_file.name)
        raw_content = pinned_file.read_text(encoding='utf-8')
        html_content, referenced = process_markdown(raw_content)
        tags = select_tags(title, raw_content)
        tags_list = ", ".join(tags)
        tags_desc = title[:80] + " — " + (tags[0] if tags else "")
        tags_html = ''.join(
            f'<a class="tag" href="../tag/{t}.html">{t}</a>' for t in tags
        ) if tags else ''
        all_referenced_media.update(referenced)
        ed = load_editorial(pinned_file.stem)
        if ed and ed[0].get("tldr"):
            tags_desc = ed[0]["tldr"][:120]
        meta = f"📅 {date_str}" if date_str else ""
        page_html = PAGE_TEMPLATE.format(
            title=html.escape(title),
            desc=html.escape(tags_desc),
            tags=html.escape(tags_list),
            site_title=SITE_TITLE,
            meta=meta,
            tags_html=tags_html,
            content=wrap_note_content(pinned_file.stem, html_content)
        )
        (PAGES_DIR / html_filename).write_text(page_html, encoding='utf-8')
        print(f"  ★ 置顶: {pinned_md}")
        # 生成置顶卡片（带头部标识）
        pinned_card = f'''<div style="background:linear-gradient(135deg,#8b6914,#a67c00);color:#fff;padding:.3rem .8rem;border-radius:.3rem;margin-bottom:.5rem;font-weight:600;font-size:.85rem;text-align:center;">★ 置顶推荐</div>'''
        pinned_html = CARD_TEMPLATE.format(
            filename=html_filename,
            title=html.escape(title),
            title_escaped=html.escape(title).lower(),
            date=date_str,
            tags=html.escape("| ".join(tags))
        )
        cards_html.insert(0, pinned_card + pinned_html)

    # ========== 处理剩余笔记 ==========
    all_md_files = []
    for md_file in md_files:
        # 检查并拆分大文件
        split_files = auto_split_large_file(md_file)
        all_md_files.extend(split_files)
    
    for md_file in all_md_files:
        title = md_file.stem
        date_str = parse_date_from_filename(md_file.name)
        html_filename = slugify(md_file.name)
        relative_path = f"notes/{html_filename}"

        # 读取并处理
        raw_content = md_file.read_text(encoding='utf-8')
        html_content, referenced = process_markdown(raw_content)

        # SEO: 选择 tags
        tags = select_tags(title, raw_content)
        tags_list = ", ".join(tags)
        tags_desc = title[:80] + " — " + (tags[0] if tags else "")
        ed = load_editorial(md_file.stem)
        if ed and ed[0].get("tldr"):
            tags_desc = ed[0]["tldr"][:120]
        tags_html = ''.join(
            f'<a class="tag" href="../tag/{t}.html">{t}</a>' for t in tags
        ) if tags else ''

        all_referenced_media.update(referenced)

        # 生成页面
        meta = f"📅 {date_str}" if date_str else ""
        page_html = PAGE_TEMPLATE.format(
            title=html.escape(title),
            desc=html.escape(tags_desc),
            tags=html.escape(tags_list),
            site_title=SITE_TITLE,
            meta=meta,
            tags_html=tags_html,
            content=wrap_note_content(md_file.stem, html_content)
        )

        (PAGES_DIR / html_filename).write_text(page_html, encoding='utf-8')

        # 生成卡片
        card_html = CARD_TEMPLATE.format(
            filename=html_filename,
            title=html.escape(title),
            title_escaped=html.escape(title).lower(),
            date=date_str,
            tags=html.escape("| ".join(tags))
        )
        cards_html.append(card_html)

        print(f"  ✓ {md_file.name}")

    # 复制引用的媒体文件
    print(f"\n复制 {len(all_referenced_media)} 个引用的媒体文件...")
    found = 0
    missing = 0
    for media_name in sorted(all_referenced_media):
        # 先在 MEDIA_DIR 找，再在 NOTES_DIR 找
        src = MEDIA_DIR / media_name
        if not src.exists():
            src = NOTES_DIR / media_name
        if src.exists():
            shutil.copy2(src, ASSETS_DIR / media_name)
            found += 1
        else:
            print(f"  ✗ 缺失: {media_name}")
            missing += 1
    print(f"  成功复制 {found} 个，缺失 {missing} 个")

    # 生成 tag 分类页面
    print("\n生成 Tag 分类页面...")
    tag_to_notes = {t: [] for t in ALL_TAGS}
    for md_file in md_files:
        title = md_file.stem
        date_str = parse_date_from_filename(md_file.name)
        html_filename = slugify(md_file.name)
        tags = select_tags(title, md_file.read_text(encoding='utf-8'))
        for tag in tags:
            tag_to_notes[tag].append({
                'title': title,
                'date': date_str,
                'filename': html_filename,
                'href': f'notes/{html_filename}'
            })

    TAG_NOTES_TEMPLATE = '<a class="tag-note-item" href="{href}"><div class="tn-title">{title}</div><div class="tn-date">{date}</div></a>'
    tag_count_total = 0
    for tag in ALL_TAGS:
        notes = tag_to_notes[tag]
        if not notes:
            continue
        notes_html = '\n'.join(
            TAG_NOTES_TEMPLATE.format(**n) for n in notes
        )
        tag_page = TAG_PAGE_TEMPLATE.format(
            tag=tag,
            site_title=SITE_TITLE,
            site_keywords=", ".join(ALL_TAGS),
            count=len(notes),
            notes=notes_html,
            generated=datetime.now().strftime("%Y-%m-%d")
        )
        tag_dir = OUTPUT_DIR / "tag"
        tag_dir.mkdir(exist_ok=True)
        (tag_dir / f"{tag}.html").write_text(tag_page, encoding='utf-8')
        tag_count_total += len(notes)
        print(f"  {tag}: {len(notes)} 篇")

    # 更新首页的卡片加入 data-tags
    tag_buttons_html = ''.join(
        f'<a class="tag-filter-btn" href="javascript:toggleTag(\'{t}\')">{t}</a>' for t in ALL_TAGS
    )
    total_count = len(md_files) + len(PINNED_NOTES)
    index_html = INDEX_TEMPLATE.format(
        site_title=SITE_TITLE,
        site_desc=f"{SITE_SUBTITLE} — 共 {total_count} 篇实战笔记",
        site_subtitle=SITE_SUBTITLE,
        count=total_count,
        cards="\n".join(cards_html),
        tag_buttons=tag_buttons_html,
        generated=datetime.now().strftime("%Y-%m-%d")
    )
    (OUTPUT_DIR / "index.html").write_text(index_html, encoding='utf-8')

    # 写入 CSS
    (OUTPUT_DIR / "style.css").write_text(CSS, encoding='utf-8')

    # 统计输出大小
    total_size = sum(f.stat().st_size for f in OUTPUT_DIR.rglob('*') if f.is_file())
    size_mb = total_size / (1024 * 1024)
    
    # 统计拆分后的文件数
    split_count = sum(1 for f in all_md_files if f.name.endswith('（上）.md') or f.name.endswith('（下）.md'))

    # 统计已附加"编者整理"文章的页面数
    ed_count = 0
    for f in PAGES_DIR.glob("*.html"):
        try:
            if '编者整理 · 主题文章' in f.read_text(encoding="utf-8"):
                ed_count += 1
        except Exception:
            pass

    print(f"\n{'=' * 60}")
    print(f"转换完成!")
    print(f"  置顶笔记: {len(PINNED_NOTES)} 篇")
    print(f"  普通笔记: {len(all_md_files)} 篇 (其中自动拆分 {split_count} 篇)")
    print(f"  总计:     {total_count} 篇")
    print(f"  编者整理: {ed_count} 篇（含主题文章）")
    print(f"  媒体文件: {found} 个")
    print(f"  输出目录: {OUTPUT_DIR}")
    print(f"  总大小:   {size_mb:.1f} MB")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
