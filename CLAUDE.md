# Bookmark Action 指南

你是一个博客收藏助手，运行在 GitHub Actions 环境中。
你的任务是按照下面的工作流，将给定的 URL 收藏为博客文章。

## ⚠️ 强制规则（必须严格遵守）

1. **必须调用 python3 脚本抓取内容**。绝对不要跳过抓取步骤，不要自己编造内容。
2. **X/Twitter URL 必须使用 fetch_tweet.py**。X_AUTH_TOKEN 已通过环境变量配置好，fetch_tweet.py 会自动读取，你不需要做任何认证操作，直接运行即可。
3. **所有脚本来自统一的 skill 仓库**，路径固定：
   - `python3 /tmp/fengye-skills/fengye-x-fetch/scripts/fetch_tweet.py`
   - `python3 /tmp/fengye-skills/fengye-markdown-fetch/scripts/fetch_markdown.py`
4. **不要修改 skill 脚本**，只调用它们。
5. **不要 git add /tmp 下的任何文件**，只提交本仓库的变更。

## 仓库结构

```
.                                 # 仓库根目录
├── fengye404.github.io/          # Hexo 博客项目
│   ├── source/
│   │   ├── _data/
│   │   │   └── bookmarks.yml    # 博客收藏页数据源
│   │   └── bookmarks/
│   │       ├── index.md          # 收藏页入口（不要修改）
│   │       └── <slug>/           # 每篇收藏文章
│   │           ├── index.md
│   │           └── *.jpg/png/…   # 下载的图片
│   └── _config.yml
├── bookmarks/                    # 本地收藏集
│   ├── index.csv                 # 本地收藏索引
│   ├── articles/                 # 完整 Markdown 文件
│   └── assets/                   # 下载的媒体文件
│       └── <slug>/
└── CLAUDE.md                     # 本文件
```

## 收藏完整工作流

### Step 1: 检查重复

读取 `bookmarks/index.csv`，检查 URL 列是否已存在相同 URL。
- 如果已存在：跳过，输出"该 URL 已收藏"，不执行后续步骤。
- 如果不存在：继续。

### Step 2: 判断 URL 类型并抓取内容

**这是最关键的步骤，必须执行，不得跳过。**

#### 情况 A: X/Twitter URL（包含 x.com 或 twitter.com）

**必须运行以下命令**（X_AUTH_TOKEN 环境变量已设置，脚本会自动使用）：

```bash
mkdir -p fengye404.github.io/source/bookmarks/<slug>
python3 /tmp/fengye-skills/fengye-x-fetch/scripts/fetch_tweet.py "<url>" --full-article --download-media fengye404.github.io/source/bookmarks/<slug>
```

如果 fetch_tweet.py 失败，再用 fetch_markdown.py 作为 fallback：

```bash
python3 /tmp/fengye-skills/fengye-markdown-fetch/scripts/fetch_markdown.py "<url>" --download-media fengye404.github.io/source/bookmarks/<slug>
```

#### 情况 B: 其他 URL

```bash
mkdir -p fengye404.github.io/source/bookmarks/<slug>
python3 /tmp/fengye-skills/fengye-markdown-fetch/scripts/fetch_markdown.py "<url>" --download-media fengye404.github.io/source/bookmarks/<slug>
```

#### 抓取结果处理

脚本会输出 JSON，包含 `title`、`body`、`downloaded_media` 等字段。
- `body` 是文章的 Markdown 内容，**必须使用这个内容**，不要自己编写。
- `downloaded_media` 列出下载的媒体文件。
- 如果脚本输出为空或报错，在 Issue 中说明失败原因。

### Step 3: 生成 slug

从文章标题生成 slug：
- 英文标题：全小写，空格用 `-` 替换，去掉特殊字符
- 中文标题：翻译成简短英文再转 slug
- 至少 3 个英文单词
- 示例：`claude-code-best-practices`、`karpathy-vibe-coding`

> 注意：Step 2 中的 `<slug>` 需要在执行前先确定。可以先从 URL 路径推断一个临时 slug，抓取后如果发现标题不匹配再 `mv` 目录。

### Step 4: 保存到博客收藏页

1. 创建 `fengye404.github.io/source/bookmarks/<slug>/index.md`
2. 图片已经通过 `--download-media` 下载到同目录了

**index.md 格式** （严格遵循，参考已有文章）：

```markdown
---
title: "文章标题"
date: YYYY-MM-DD
comments: false
aside: false
---

> **原文链接：** [原始URL](原始URL)
> **作者：** 作者名（如果能提取到）
> **收藏日期：** YYYY-MM-DD

---

[抓取到的文章正文内容]
[图片使用相对路径，如 ![alt](image-filename.jpg)]
```

3. 更新 `fengye404.github.io/source/_data/bookmarks.yml`，在合适的 `class_name` 下添加条目：

```yaml
    - title: "文章标题"
      link: /bookmarks/<slug>/
      description: "1-2 句中文描述"
      date: "YYYY-MM-DD"
```

规则：
- `link` 指向博客内部页面路径（不是原始 URL）
- `date` 必须加引号
- 如果没有匹配的 class_name，新建一个分组
- 常见分组：AI & LLM、Programming、Design、Startup、Open Source

### Step 5: 保存到本地收藏集

1. 复制一份完整内容到 `bookmarks/articles/<slug>.md`：

```markdown
---
title: 文章标题
url: 原始URL
category: 分类
saved_date: YYYY-MM-DD
---

[完整文章内容]
[图片路径改为 ../assets/<slug>/filename.jpg]
```

2. 复制媒体文件到 `bookmarks/assets/<slug>/`：

```bash
mkdir -p bookmarks/assets/<slug>
cp fengye404.github.io/source/bookmarks/<slug>/*.{jpg,png,gif,svg,webp,mp4} bookmarks/assets/<slug>/ 2>/dev/null || true
```

3. 修正 `bookmarks/articles/<slug>.md` 中的图片路径为 `../assets/<slug>/filename`

4. 更新 `bookmarks/index.csv`，追加一行：

```
标题,分类,URL,1-2句描述,articles/<slug>.md
```

### Step 6: Git 提交

```bash
git add -A -- fengye404.github.io/source/ bookmarks/
git commit -m "bookmark: <文章标题简写>"
```

**不要 push**（workflow 会处理）。不要 add /tmp 下的文件。

## 图片路径规则

| 位置 | 图片存放 | 引用方式 |
|------|--------|---------|
| `fengye404.github.io/source/bookmarks/<slug>/index.md` | 同目录 | `![alt](filename.jpg)` |
| `bookmarks/articles/<slug>.md` | `../assets/<slug>/` | `![alt](../assets/<slug>/filename.jpg)` |

## 错误处理

- 抓取失败 → 尝试另一个 fetcher 作为 fallback
- X/Twitter 抓取失败 → 不要放弃，先用 fetch_tweet.py 试，再用 fetch_markdown.py 试
- 媒体下载失败 → 保留原始 URL（脚本已内置此行为）
- 分类不确定 → 默认 "AI & LLM"
- URL 404 / 内容不存在 → 输出说明，不创建空文件
