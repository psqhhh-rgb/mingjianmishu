#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
给不带日期的笔记文件名添加日期前缀。
策略：
1. 尝试从内容中提取日期
2. 如果找不到，用文件修改时间作为日期
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime

NOTES_DIR = Path(r"E:\psqhhh\民间奇门法术实战应用")

def find_date_in_content(filepath: Path) -> str:
    """从笔记内容中提取日期字符串 YYYY-MM-DD"""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception:
        return ""

    # 优先匹配 YYYY-MM-DD 格式
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', content)
    if m:
        yyyy, mm, dd = m.group(1), m.group(2), m.group(3)
        if 2020 <= int(yyyy) <= 2030 and 1 <= int(mm) <= 12 and 1 <= int(dd) <= 31:
            return f"{yyyy}-{mm}-{dd}"

    # 匹配 YYYYMMDD 格式
    m = re.search(r'(\d{4})(\d{2})(\d{2})', content)
    if m:
        yyyy, mm, dd = m.group(1), m.group(2), m.group(3)
        if 2020 <= int(yyyy) <= 2030 and 1 <= int(mm) <= 12 and 1 <= int(dd) <= 31:
            return f"{yyyy}-{mm}-{dd}"

    return ""

def get_modification_date(filepath: Path) -> str:
    """用文件最后修改时间作为日期"""
    try:
        mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
        return mtime.strftime("%Y-%m-%d")
    except Exception:
        return ""

def main():
    # 找出所有不带日期前缀的 .md 文件
    notes = sorted(NOTES_DIR.glob("*.md"))
    
    renamed = []
    skipped = []
    no_date_change = []

    for note in notes:
        stem = note.stem
        # 检查是否已有日期前缀
        if re.match(r'^\d{8}', stem):
            renamed.append(note.name)  # 已有日期，不算重命名
            continue

        # 1. 从内容中找日期
        date_str = find_date_in_content(note)
        
        # 2. 找不到就用文件修改时间
        if not date_str:
            date_str = get_modification_date(note)

        if not date_str:
            skipped.append(note.name)
            continue

        date_num = date_str.replace("-", "")
        
        # 新文件名
        new_name = f"{date_num}{stem}.md"
        
        # 避免冲突
        final_path = NOTES_DIR / new_name
        counter = 1
        while final_path.exists():
            base = new_name[:-3]
            final_path = NOTES_DIR / f"{base}_{counter}.md"
            counter += 1

        # 重命名
        note.rename(final_path)
        renamed.append(f"{note.name} → {final_path.name}")
        print(f"  ✓ {note.name} → {final_path.name}")
        no_date_change.append((note.name, final_path.name, date_str))

    if skipped:
        print(f"\n⚠ 无法确定日期的笔记 ({len(skipped)} 篇):")
        for s in skipped:
            print(f"    {s}")

    print(f"\n统计:")
    print(f"  已有日期: {sum(1 for n in renamed if '→' not in n)} 篇")
    print(f"  新重命名: {sum(1 for n in renamed if '→' in n)} 篇")
    print(f"  未找到日期: {len(skipped)} 篇")

if __name__ == "__main__":
    main()
