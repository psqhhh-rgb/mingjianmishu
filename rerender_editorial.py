#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
重渲染「编者整理」区块：只改 editorial/<stem>.md 对应的既有页面，不动原始对话记录。

背景：build_site.py 会 rm -rf docs 重建（源笔记目录已只剩增量笔记，会丢页）；
update_site.py 只追加新页。已上线页面要改编者整理时，用本脚本就地替换
<div class="divider-note"> ... </article> 之间那段，并同步 meta description。

用法：
  python rerender_editorial.py            # 自动检测：editorial 比页面新的
  python rerender_editorial.py --all      # 全部重渲染
  python rerender_editorial.py --only 20261019评选三好学生，白亮，我说必中 [...]
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import html
import re
from pathlib import Path

import obsidian_to_web as ow

PAGES = ow.PAGES_DIR
EDITORIAL = ow.EDITORIAL_DIR
MARK = '<div class="divider-note">以下为编者整理的主题文章</div>'
DESC_RE = re.compile(r'<meta name="description" content="(.*?)">', re.S)


def page_for(stem: str) -> Path:
    return PAGES / ow.slugify(stem + ".md")


def rerender(stem: str, dry: bool = False) -> str:
    path = page_for(stem)
    if not path.exists():
        return f"  ! 页面不存在: {stem}"
    new_block = ow.render_editorial(stem)
    if not new_block:
        return f"  ! 无编者整理: {stem}"

    text = path.read_text(encoding="utf-8")
    start = text.find(MARK)
    if start == -1:
        return f"  ! 页内无编者区块: {stem}"
    end = text.rfind("</article>")
    if end == -1 or end < start:
        return f"  ! 结构异常: {stem}"

    text = text[:start] + new_block + "\n  " + text[end:]

    meta = ow.load_editorial(stem)[0]
    tldr = meta.get("tldr", "")
    if tldr:
        m = DESC_RE.search(text)
        if m:
            text = text[: m.start(1)] + html.escape(tldr[:120]) + text[m.end(1):]

    if not dry:
        path.write_text(text, encoding="utf-8")
    return f"  ~ 重渲染: {path.name}"


def main():
    dry = "--dry-run" in sys.argv
    only = []
    if "--only" in sys.argv:
        i = sys.argv.index("--only")
        only = [a for a in sys.argv[i + 1:] if not a.startswith("--")]

    stems = []
    if only:
        stems = only
    else:
        for f in sorted(EDITORIAL.glob("*.md")):
            stem = f.name[:-3]
            p = page_for(stem)
            if not p.exists():
                continue
            if "--all" in sys.argv or f.stat().st_mtime > p.stat().st_mtime:
                stems.append(stem)

    if not stems:
        print("没有需要重渲染的页面。")
        return

    print(f"待处理 {len(stems)} 篇", "· DRY RUN" if dry else "")
    for s in stems:
        print(rerender(s, dry))


if __name__ == "__main__":
    main()
