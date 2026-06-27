# 民间奇门法术实战应用 - Obsidian 笔记网站

将 Obsidian 笔记自动转换为静态网站，部署到 GitHub Pages。

## 目录结构

```
.
├── docs/                    # 网站静态文件（GitHub Pages 部署源）
│   ├── index.html           # 首页（笔记目录 + 搜索）
│   ├── style.css            # 样式
│   ├── notes/               # 所有笔记 HTML 页面
│   └── assets/              # 图片、视频等媒体文件
├── obsidian_to_web.py       # 转换脚本
└── .github/workflows/       # GitHub Actions 自动部署
    └── deploy.yml
```

## 使用方法

### 1. 更新笔记内容

当 Obsidian 笔记有更新时，重新运行转换脚本：

```bash
python obsidian_to_web.py
```

脚本会读取 `E:\psqhhh\民间奇门法术实战应用` 下的所有 `.md` 文件，
从 `E:\psqhhh\` 复制引用的图片/视频，生成 `docs/` 目录。

### 2. 部署到 GitHub Pages

```bash
git add docs/
git commit -m "更新笔记内容"
git push
```

推送后 GitHub Actions 会自动部署。
在仓库 Settings → Pages → Source 选择 **GitHub Actions**。

### 3. 访问网站

部署成功后访问：
```
https://<你的用户名>.github.io/<仓库名>/
```

## 配置说明

如需修改笔记源目录或网站标题，编辑 `obsidian_to_web.py` 顶部的配置：

```python
NOTES_DIR = Path(r"E:\psqhhh\民间奇门法术实战应用")
MEDIA_DIR = Path(r"E:\psqhhh")
SITE_TITLE = "民间奇门法术实战应用"
SITE_SUBTITLE = "紫鸢真人传授 · 笔记整理"
```

## 注意事项

- GitHub Pages 仓库建议不超过 1GB，当前站点约 612MB
- 视频文件较大，首次推送可能需要较长时间
- 10 个媒体文件缺失（源文件不存在），不影响其他内容显示
