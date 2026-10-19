#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
增量更新：把「民间秘术」目录里的新笔记追加到既有站点，不重建已有页面。

背景：源笔记目录已改为 E:\psqhhh\民间秘术（只保留新笔记），
若跑 build_site.py 会 rm -rf docs 重建，导致既有 218 页丢失。
因此本脚本只做“追加”：

  1) 只渲染 docs/notes 里尚不存在的笔记页
  2) 复制这些页引用的媒体到 docs/assets
  3) 把新卡片插到首页置顶之后，并更新“共 N 篇笔记”
  4) 以 docs/notes/*.html 为数据源重建 7 个 tag 页
  5) 三件套 + JSON-LD 交给 gen_geo_assets.py / inject_geo_schema.py（另行调用）

用法：python update_site.py [--dry-run]
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import re
import html
import shutil
from pathlib import Path
from datetime import datetime

import obsidian_to_web as ow

SRC_DIR = Path(r"E:\psqhhh\民间秘术")
MEDIA_DIR = Path(r"E:\psqhhh")

DOCS = ow.OUTPUT_DIR
PAGES = ow.PAGES_DIR
ASSETS = ow.ASSETS_DIR
INDEX = DOCS / "index.html"

ow.NOTES_DIR = SRC_DIR
ow.MEDIA_DIR = MEDIA_DIR

TAG_RE = re.compile(r'class="tag" href="\.\./tag/([^"]+)\.html"')
TITLE_RE = re.compile(r'<h1 class="article-title">(.*?)</h1>', re.S)
DATE_RE = re.compile(r'<div class="article-meta">\s*📅\s*([0-9]{4}-[0-9]{2}-[0-9]{2})')
STATS_RE = re.compile(r'(<div class="stats">共 )(\d+)( 篇笔记</div>)')


def render_new_notes(dry_run: bool):
    """渲染新笔记，返回 (cards, media_copied, missing, new_slugs, new_items)。"""
    cards, new_slugs, new_items, copied, missing = [], [], [], 0, []

    files = sorted(SRC_DIR.glob("*.md"), key=lambda f: f.name, reverse=True)
    for f in files:
        if not ow.parse_date_from_filename(f.name) or f.stat().st_size == 0:
            continue
        slug = ow.slugify(f.name)
        if (PAGES / slug).exists():
            print(f"  = 已存在，跳过: {f.name}")
            continue

        raw = f.read_text(encoding="utf-8")
        content, refs = ow.process_markdown(raw)
        tags = ow.select_tags(f.stem, raw)
        ed = ow.load_editorial(f.stem)
        if ed and ed[0].get("tldr"):
            desc = ed[0]["tldr"][:120]
        else:
            desc = f.stem[:80] + " — " + (tags[0] if tags else "")
        date_str = ow.parse_date_from_filename(f.name)

        page = ow.PAGE_TEMPLATE.format(
            title=html.escape(f.stem),
            desc=html.escape(desc),
            tags=html.escape(", ".join(tags)),
            site_title=ow.SITE_TITLE,
            meta=f"📅 {date_str}",
            tags_html="".join(f'<a class="tag" href="../tag/{t}.html">{t}</a>' for t in tags),
            content=ow.wrap_note_content(f.stem, content),
        )
        if not dry_run:
            (PAGES / slug).write_text(page, encoding="utf-8")

        # 媒体
        for name in sorted(refs):
            src = MEDIA_DIR / name
            if not src.exists():
                src = SRC_DIR / name
            dst = ASSETS / name
            if src.exists():
                if not dry_run and not dst.exists():
                    shutil.copy2(src, dst)
                    copied += 1
            else:
                missing.append(name)

        cards.append(ow.CARD_TEMPLATE.format(
            filename=slug,
            title=html.escape(f.stem),
            title_escaped=html.escape(f.stem).lower(),
            date=date_str,
            tags=html.escape("|".join(tags)),
        ))
        new_slugs.append(f.stem)
        new_items.append({
            "slug": slug,
            "title": f.stem,
            "date": date_str,
            "tags": tags,
        })
        print(f"  + 新增: {f.name}  ->  {slug}  [{', '.join(tags)}]")

    return cards, copied, missing, new_slugs, new_items


def insert_into_index(cards, dry_run: bool):
    if not cards:
        return 0
    text = INDEX.read_text(encoding="utf-8")

    idx = text.rfind("★ 置顶推荐")
    if idx != -1:
        end = text.find("</a>", idx)
        pos = end + len("</a>")
    else:
        marker = '<main class="notes-grid">'
        pos = text.find(marker) + len(marker)

    block = "\n" + "\n".join(cards)
    text = text[:pos] + block + text[pos:]

    m = STATS_RE.search(text)
    old_count = int(m.group(2)) if m else 0
    if m:
        text = STATS_RE.sub(
            lambda mm: f"{mm.group(1)}{int(mm.group(2)) + len(cards)}{mm.group(3)}", text, count=1
        )

    if not dry_run:
        INDEX.write_text(text, encoding="utf-8")
    return old_count


def append_to_tag_pages(new_items, dry_run: bool):
    """把新笔记追加到既有 tag 页（不重建，避免改动原有归类）。"""
    by_tag = {t: [] for t in ow.ALL_TAGS}
    for it in new_items:
        for tag in it["tags"]:
            if tag in by_tag:
                by_tag[tag].append(it)

    item_tpl = ('<a class="tag-note-item" href="notes/{slug}"><div class="tn-title">'
                '{title}</div><div class="tn-date">{date}</div></a>')

    for tag, items in by_tag.items():
        if not items:
            continue
        path = DOCS / "tag" / f"{tag}.html"
        if not path.exists():
            print(f"  ! tag 页不存在: {tag}")
            continue
        text = path.read_text(encoding="utf-8")

        marker = '<div class="tag-notes-list">'
        if marker not in text:
            print(f"  ! 结构不符: {tag}")
            continue
        block = "\n".join(item_tpl.format(**it) for it in items)
        text = text.replace(marker, marker + "\n" + block, 1)

        # 计数 +N
        m = re.search(r'<span class="site-name">([^<]*?)· (\d+) 篇</span>', text)
        if m:
            new_n = int(m.group(2)) + len(items)
            text = text.replace(
                m.group(0),
                f'<span class="site-name">{m.group(1)}· {new_n} 篇</span>',
                1,
            )
            text = re.sub(r"中的\d+篇笔记", f"中的{new_n}篇笔记", text, count=1)

        if not dry_run:
            path.write_text(text, encoding="utf-8")
        print(f"  tag {tag}: +{len(items)}")

    return sum(len(v) for v in by_tag.values())


def main():
    dry = "--dry-run" in sys.argv
    print("=" * 60)
    print("增量更新（追加模式）", "· DRY RUN" if dry else "")
    print("=" * 60)

    print(f"\n源目录: {SRC_DIR}")
    print(f"既有页面: {len(list(PAGES.glob('*.html')))} 篇\n")

    cards, copied, missing, stems, new_items = render_new_notes(dry)
    old_count = insert_into_index(cards, dry)
    print()
    tag_links = append_to_tag_pages(new_items, dry)

    print(f"\n{'=' * 60}")
    print(f"新笔记: {len(stems)} 篇")
    print(f"复制媒体: {copied} 个" + (f"，缺失 {len(missing)} 个: {missing}" if missing else ""))
    print(f"首页笔记数: {old_count} -> {old_count + len(cards)}")
    print(f"tag 追加链接: {tag_links} 条")
    print(f"页面总数: {len(list(PAGES.glob('*.html')))}")
    print("=" * 60)


if __name__ == "__main__":
    main()
