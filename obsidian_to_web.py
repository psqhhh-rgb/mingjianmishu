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

SITE_TITLE = "民间奇门法术实战应用"
SITE_SUBTITLE = "紫鸢真人传授 · 笔记整理"

# ============ 模板 ============
PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - {site_title}</title>
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
</header>
<main class="notes-grid">
{cards}
</main>
<footer class="footer">
  <p>由 Obsidian 笔记自动生成 · {generated}</p>
</footer>
<script>
const searchInput = document.getElementById('searchInput');
searchInput.addEventListener('input', function() {{
  const q = this.value.toLowerCase().trim();
  document.querySelectorAll('.note-card').forEach(card => {{
    const title = card.dataset.title.toLowerCase();
    card.style.display = (!q || title.includes(q)) ? '' : 'none';
  }});
}});
</script>
</body>
</html>"""

CARD_TEMPLATE = """<a class="note-card" href="notes/{filename}" data-title="{title_escaped}">
  <div class="card-body">
    <div class="card-title">{title}</div>
    <div class="card-date">{date}</div>
  </div>
</a>"""

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
.article blockquote{border-left:3px solid var(--accent);padding-left:1rem;
  margin:1rem 0;color:var(--muted)}
.article code{background:var(--border);padding:.1rem .3rem;border-radius:.2rem;font-size:.9em}
.article pre{background:#2c2418;color:#f0e8d8;padding:1rem;border-radius:.5rem;
  overflow-x:auto;margin:1rem 0}
.article pre code{background:none;padding:0}
.article table{width:100%;border-collapse:collapse;margin:1rem 0}
.article th,.article td{border:1px solid var(--border);padding:.5rem .8rem;text-align:left}
.article th{background:var(--card)}

.footer{text-align:center;padding:2rem;color:var(--muted);font-size:.8rem}

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
    """将文件名转为 URL 安全的 HTML 文件名"""
    stem = Path(filename).stem
    # 保留中文，只替换不安全字符
    safe = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', stem)
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


def main():
    print("=" * 60)
    print("Obsidian → 静态网站转换器")
    print("=" * 60)

    # 清理输出目录
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)
    ASSETS_DIR.mkdir()
    PAGES_DIR.mkdir()

    # 收集所有 markdown 文件
    md_files = sorted(NOTES_DIR.glob("*.md"), key=lambda f: f.name, reverse=True)
    print(f"\n找到 {len(md_files)} 篇笔记")

    all_referenced_media = set()
    cards_html = []

    for md_file in md_files:
        title = md_file.stem
        date_str = parse_date_from_filename(md_file.name)
        html_filename = slugify(md_file.name)
        relative_path = f"notes/{html_filename}"

        # 读取并处理
        content = md_file.read_text(encoding='utf-8')
        html_content, referenced = process_markdown(content)

        all_referenced_media.update(referenced)

        # 生成页面
        meta = f"📅 {date_str}" if date_str else ""
        page_html = PAGE_TEMPLATE.format(
            title=html.escape(title),
            site_title=SITE_TITLE,
            meta=meta,
            content=html_content
        )

        (PAGES_DIR / html_filename).write_text(page_html, encoding='utf-8')

        # 生成卡片
        card_html = CARD_TEMPLATE.format(
            filename=html_filename,
            title=html.escape(title),
            title_escaped=html.escape(title).lower(),
            date=date_str
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

    # 生成 index.html
    index_html = INDEX_TEMPLATE.format(
        site_title=SITE_TITLE,
        site_subtitle=SITE_SUBTITLE,
        count=len(md_files),
        cards="\n".join(cards_html),
        generated=datetime.now().strftime("%Y-%m-%d")
    )
    (OUTPUT_DIR / "index.html").write_text(index_html, encoding='utf-8')

    # 写入 CSS
    (OUTPUT_DIR / "style.css").write_text(CSS, encoding='utf-8')

    # 统计输出大小
    total_size = sum(f.stat().st_size for f in OUTPUT_DIR.rglob('*') if f.is_file())
    size_mb = total_size / (1024 * 1024)

    print(f"\n{'=' * 60}")
    print(f"转换完成!")
    print(f"  笔记页面: {len(md_files)} 篇")
    print(f"  媒体文件: {found} 个")
    print(f"  输出目录: {OUTPUT_DIR}")
    print(f"  总大小:   {size_mb:.1f} MB")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
