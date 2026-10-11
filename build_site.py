#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mingjianmishu 一键构建脚本
流程：
  1) obsidian_to_web.py      重新生成 docs/（含"编者整理"文章注入）
  2) gen_geo_assets.py       重新生成 robots.txt / sitemap.xml / llms.txt 到 geo-kit/
  3) 复制三件套到 docs/
  4) inject_geo_schema.py --apply   给全站注入 JSON-LD
  5) 清理 docs/ 下注入产生的 .bak 备份
用法： python build_site.py
"""
import subprocess
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
GEOKIT = ROOT / "geo-kit"
PY = sys.executable


def run(script, *args):
    print(f"\n>>> {script} {' '.join(args)}".strip())
    subprocess.run([PY, str(ROOT / script), *args], check=True, cwd=str(ROOT))


def main():
    # 1) 转换（含编者整理注入）
    run("obsidian_to_web.py")

    # 2) 生成 GEO 三件套
    run("geo-kit/gen_geo_assets.py")

    # 3) 复制三件套到 docs/
    for name in ("robots.txt", "llms.txt", "sitemap.xml"):
        shutil.copy2(GEOKIT / name, DOCS / name)
        print(f"  复制 {name} -> docs/")

    # 4) 注入 JSON-LD
    run("geo-kit/inject_geo_schema.py", "--apply")

    print("\n构建完成。下一步：git add -A && git commit，然后推送。")


if __name__ == "__main__":
    main()
