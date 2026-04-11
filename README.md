# blog

fengye's blog 的完整工作区，包含 Hexo 博客和收藏系统。

线上地址：[fengye404.top](https://fengye404.top)

## 仓库结构

```
.
├── fengye404.github.io/       # Hexo 博客项目
│   ├── _config.yml            # Hexo 配置
│   ├── source/
│   │   ├── _posts/            # 博客文章
│   │   ├── _data/bookmarks.yml  # 收藏页数据
│   │   └── bookmarks/         # 收藏文章页面
│   └── themes/butterfly/      # 主题
├── bookmarks/                 # 本地收藏集
│   ├── index.csv              # 收藏索引
│   ├── articles/              # 完整 Markdown 存档
│   └── assets/                # 媒体文件
├── .github/workflows/
│   └── bookmark.yml           # 远程收藏 Action
├── CLAUDE.md                  # 收藏 Agent 指令
└── git-sync                   # 一键同步脚本
```

## 分支

| 分支 | 用途 |
|---|---|
| `hexo-source` | 默认分支，所有源码 |
| `gh-pages` | Hexo 生成的静态站点（自动部署） |

## 常用操作

### 写文章

```bash
cd fengye404.github.io
npx hexo new "文章标题"
# 编辑 source/_posts/文章标题.md
```

### 本地预览

```bash
cd fengye404.github.io
npx hexo server
# 访问 http://localhost:4000
```

### 发布

```bash
cd fengye404.github.io
npx hexo clean && npx hexo deploy
```

### 同步源码到 GitHub

```bash
./git-sync
```

## 收藏系统

两种收藏方式：

- **本地收藏**：通过 `fengye-bookmark` skill 直接在终端操作
- **远程收藏**：在 GitHub 创建 Issue，标题填 URL，加 `bookmark` 标签，Action 自动抓取并提交

收藏内容同时写入两处：
1. `fengye404.github.io/source/bookmarks/<slug>/` — 博客页面
2. `bookmarks/articles/<slug>.md` — 本地存档

## 技术栈

- Hexo 7.3.0 + Butterfly 5.5.4
- GitHub Pages（自定义域名 fengye404.top）
- GitHub Actions + Claude Code（远程收藏）
