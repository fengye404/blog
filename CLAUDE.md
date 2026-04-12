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

### Step 2: 抓取内容

**这是最关键的步骤，必须执行，不得跳过。**

> **⚠️ 性能关键：所有脚本输出必须重定向到文件，禁止让输出打到 stdout！**
> 脚本输出可达 20KB+，如果打到 stdout 会膨胀你的对话上下文，导致后续每一步都变慢。
> 用 `> /tmp/result_X.md` 保存，用 `wc -c` 和 `head` 查看摘要。

先创建媒体目录：

```bash
mkdir -p fengye404.github.io/source/bookmarks/<slug>
```

#### 情况 A: X/Twitter URL（包含 x.com 或 twitter.com）

**第一步：运行 fetch_tweet.py，输出保存到文件**：

```bash
python3 /tmp/fengye-skills/fengye-x-fetch/scripts/fetch_tweet.py "<url>" \
  --full-article --download-media fengye404.github.io/source/bookmarks/<slug> \
  > /tmp/result_tweet.md 2>/tmp/err_tweet.txt
echo "=== fetch_tweet.py: $(wc -c < /tmp/result_tweet.md) bytes ==="
head -3 /tmp/result_tweet.md
```

**第二步：判断是否需要继续抓取**：

- 如果 `/tmp/result_tweet.md` **≥ 5000 字节**：说明 fetch_tweet.py 已获取到完整内容（X Article 或长推文），**跳过 fetch_markdown.py**，直接使用 `/tmp/result_tweet.md`。
- 如果 `/tmp/result_tweet.md` **< 5000 字节**：说明是短推文，需要继续。

**第三步（仅短推文时执行）：检查外部链接并抓取**：

```bash
# 在推文内容中查找外部链接（排除 x.com/twitter.com/t.co）
grep -oP 'https?://[^\s)]+' /tmp/result_tweet.md | grep -v -E 'x\.com|twitter\.com|t\.co' | head -3
```

如果找到外部文章链接（如 `anthropic.com/...`、`medium.com/...` 等），抓取那个链接：
```bash
python3 /tmp/fengye-skills/fengye-markdown-fetch/scripts/fetch_markdown.py "<外部文章URL>" \
  --download-media fengye404.github.io/source/bookmarks/<slug> \
  > /tmp/result_external.md 2>/tmp/err_external.txt
echo "=== fetch_markdown.py (external): $(wc -c < /tmp/result_external.md) bytes ==="
head -3 /tmp/result_external.md
```

如果没有外部链接，运行 fetch_markdown.py 抓推文页面作为备选：
```bash
python3 /tmp/fengye-skills/fengye-markdown-fetch/scripts/fetch_markdown.py "<url>" \
  --download-media fengye404.github.io/source/bookmarks/<slug> \
  > /tmp/result_md.md 2>/tmp/err_md.txt
echo "=== fetch_markdown.py (tweet): $(wc -c < /tmp/result_md.md) bytes ==="
head -3 /tmp/result_md.md
```

> **⚠️ 大多数值得收藏的 X 链接是分享文章的 tweet。** 真正有价值的内容在外部链接里，不是 tweet 本身。如果有外部链接，优先用外部链接的结果。

**第四步：选择最佳结果（用文件大小判断，不要 cat 文件内容！）**：

```bash
wc -c /tmp/result_*.md
```

选择 **字节数最大** 的文件。如果有外部文章结果，几乎 100% 应该用它。
将最佳结果记为 `BEST_RESULT`（如 `/tmp/result_external.md`）。

#### 情况 B: 其他 URL

```bash
python3 /tmp/fengye-skills/fengye-markdown-fetch/scripts/fetch_markdown.py "<url>" \
  --download-media fengye404.github.io/source/bookmarks/<slug> \
  > /tmp/result_md.md 2>/tmp/err_md.txt
echo "=== fetch_markdown.py: $(wc -c < /tmp/result_md.md) bytes ==="
head -3 /tmp/result_md.md
```

`BEST_RESULT` = `/tmp/result_md.md`

#### 抓取结果处理

- 脚本输出 Markdown 格式的文章内容，已保存在 `/tmp/result_*.md` 文件中。
- **必须使用脚本抓取的内容**，不要自己编写文章内容。
- 如果所有结果文件都小于 100 字节 → 视为抓取失败，停止并报告。
- 如果只有一个成功，使用成功的那个。

### Step 3: 生成 slug

从文章标题生成 slug：
- 英文标题：全小写，空格用 `-` 替换，去掉特殊字符
- 中文标题：翻译成简短英文再转 slug
- 至少 3 个英文单词
- 示例：`claude-code-best-practices`、`karpathy-vibe-coding`

> 注意：Step 2 中的 `<slug>` 需要在执行前先确定。可以先从 URL 路径推断一个临时 slug，抓取后如果发现标题不匹配再 `mv` 目录。

### Step 4: 保存到博客收藏页

1. 从 `BEST_RESULT` 文件生成 `fengye404.github.io/source/bookmarks/<slug>/index.md`：

```bash
# 提取标题（第一行去掉 # 前缀）
TITLE=$(head -1 "$BEST_RESULT" | sed 's/^#\+ //')

# 生成 index.md：frontmatter + 原文链接 + 正文内容
cat > fengye404.github.io/source/bookmarks/<slug>/index.md << 'FRONTMATTER'
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

FRONTMATTER
cat "$BEST_RESULT" >> fengye404.github.io/source/bookmarks/<slug>/index.md
```

> **注意**：上面的 `cat > ... << FRONTMATTER` 中的字段需要替换为实际值。如果 `BEST_RESULT` 第一行是标题行（`# xxx`），可以跳过它避免重复。

2. **修正图片路径**：`BEST_RESULT` 中的图片路径可能是绝对路径（如 `/tmp/...` 或 `fengye404.github.io/source/bookmarks/<slug>/xxx.jpg`），需要改为相对路径：

```bash
sed -i 's|fengye404.github.io/source/bookmarks/<slug>/||g' fengye404.github.io/source/bookmarks/<slug>/index.md
sed -i 's|/tmp/[^)]*\(\/[^/)]*\.\(jpg\|png\|gif\|svg\|webp\)\)|\1|g' fengye404.github.io/source/bookmarks/<slug>/index.md
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

1. 从 `BEST_RESULT` 生成 `bookmarks/articles/<slug>.md`：

```bash
# 生成 frontmatter + 正文
cat > bookmarks/articles/<slug>.md << 'EOF'
---
title: 文章标题
url: 原始URL
category: 分类
saved_date: YYYY-MM-DD
---

EOF
cat "$BEST_RESULT" >> bookmarks/articles/<slug>.md
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

- 如果所有结果文件小于 100 字节 → 视为抓取失败，在 Issue 中说明失败原因，不创建空文件，不要反复尝试不同方法
- 媒体下载失败 → 保留原始 URL（脚本已内置此行为）
- 分类不确定 → 默认 "AI & LLM"
- URL 404 / 内容不存在 → 输出说明，不创建空文件

## 性能规则（必须遵守）

- **绝对不要 `cat` 或 `echo` 大文件内容到你的对话**。如果需要查看内容，用 `head -5` 或 `wc -c`。
- 创建 index.md 和 articles/*.md 时，使用 `cat > file << EOF ... EOF` + `cat "$BEST_RESULT" >> file`，不要把文件内容复制到命令中。
- 比较结果用 `wc -c`（文件大小），不要读取全部内容来比较。
