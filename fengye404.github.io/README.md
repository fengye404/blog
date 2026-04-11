# fengye404.github.io

基于 Hexo 的个人博客源码仓库，使用 GitHub Pages 托管静态站点，主题为 Butterfly。

## 当前仓库状态（基于 2026-03-07 本地检查）

- 博客框架：`Hexo 7.3.0`
- 主题：`butterfly`（本地目录 `themes/butterfly`）
- 源码分支：`hexo-source`（当前分支）
- 发布分支：`gh-pages`（`hexo deploy` 推送目标）
- 远程仓库：`https://github.com/fengye404/fengye404.github.io.git`
- 线上地址（配置）：`https://fengye404.top`
- 自定义域名文件：`source/CNAME`（内容：`fengye404.top`）
- 文章规模：
  - `source/_posts` 下约 `32` 篇 Markdown 文章（一级）
  - 文章配图等资源文件约 `138` 个（子目录）
- 当前工作区状态：干净（无未提交修改）
- 自动依赖更新：`.github/dependabot.yml`（npm，daily）

## 技术栈与依赖

- Node.js（建议 LTS，如 18/20）
- npm
- Hexo 及核心依赖：
  - `hexo`
  - `hexo-deployer-git`
  - `hexo-generator-*`（index/tag/category/archive/search）
  - `hexo-renderer-*`（marked/pug/ejs/stylus）
  - `hexo-server`
  - `hexo-wordcount`

安装依赖：

```bash
npm install
```

## 当前目录标准操作（写作 -> 发布 -> Push）

下面是在当前目录 `/Users/fengye/workspace/blog/fengye404.github.io` 的推荐流程。

1. 写一篇新的博客

```bash
cd /Users/fengye/workspace/blog/fengye404.github.io
hexo new "你的文章标题"
```

生成后编辑：

- 文章文件：`source/_posts/你的文章标题.md`
- 文章资源目录（图片等）：`source/_posts/你的文章标题/`

2. 推送并发布（发布静态站点到 `gh-pages`）

```bash
cd /Users/fengye/workspace/blog/fengye404.github.io
hexo clean
hexo generate
hexo deploy
```

这一步会把 `public/` 的内容发布到远程 `gh-pages` 分支（GitHub Pages 实际站点内容）。

3. Push 到 GitHub（推送源码分支 `hexo-source`）

```bash
cd /Users/fengye/workspace/blog/fengye404.github.io
git add .
git commit -m "feat: publish new post"
git push origin hexo-source
```

如果只是快速备份源码，也可以使用仓库里的脚本：

```bash
./backup.sh
```

## 关键配置说明

核心配置文件：`_config.yml`

- 主题：`theme: butterfly`
- URL：`url: https://fengye404.top`
- 部署：
  - `type: git`
  - `repo: https://github.com/fengye404/fengye404.github.io`
  - `branch: gh-pages`
- 固定链接：`:year/:month/:day/:title/`
- 文章资源目录：`post_asset_folder: true`
- 搜索：已启用 `hexo-generator-search`，输出 `search.xml`
- `future: true`（未来日期文章也会参与生成）

主题配置文件：`themes/butterfly/_config.yml`

- 已启用/设置较明确：
  - 本地搜索：`search.use: local_search`
  - 字数统计：`wordcount.enable: true`
  - Busuanzi：`site_uv/site_pv/page_pv: true`
  - 目录（TOC）：文章页开启
  - 深色模式：开启（手动切换）
- 未启用：
  - 评论系统（`comments.use` 为空）
  - PWA、PJAX、Lazyload（默认关闭）

## 本地开发

启动本地服务：

```bash
hexo server
```

默认访问地址：

- `http://localhost:4000`

常用命令：

```bash
hexo clean     # 清理缓存与生成目录
hexo generate  # 生成静态文件
hexo server    # 本地预览
hexo deploy    # 发布到 gh-pages
```

说明：`npm run clean/build/server/deploy` 在本仓库中是上述 Hexo 命令的等价封装。

## 写作与内容管理

创建新文章：

```bash
hexo new "文章标题"
```

由于已开启 `post_asset_folder: true`，建议将文章图片放在与文章同名的资源目录中（`source/_posts/<文章名>/`），并使用相对路径引用。

当前脚手架 `scaffolds/post.md` 包含：

- `title`
- `date`
- `tags`
- `typora-root-url: ./{{ title }}`

## 部署流程（GitHub Pages）

推荐发布步骤：

```bash
hexo clean
hexo generate
hexo deploy
```

说明：

- `hexo generate` 会生成 `public/` 静态文件。
- `hexo deploy` 通过 `hexo-deployer-git` 将内容推送到同仓库 `gh-pages` 分支。
- 需要在 GitHub 仓库设置里确认 Pages 指向 `gh-pages` 分支（root）。
- 自定义域名由 `source/CNAME` 管理，发布后会带到站点。

## 目录结构（核心）

```text
.
├── _config.yml                # Hexo 主配置
├── package.json               # npm 脚本与依赖
├── source/
│   ├── CNAME                  # 自定义域名
│   └── _posts/                # 文章与文章资源
├── themes/
│   └── butterfly/             # Butterfly 主题源码
├── scaffolds/                 # 新建文章/页面模板
├── public/                    # 本地生成静态文件（忽略）
├── node_modules/              # 本地依赖（忽略）
└── .deploy_git/               # Hexo 部署缓存仓库（忽略）
```

## 备份脚本

仓库内提供：

- `backup.sh`
- `backup.bat`

作用：执行 `git add . && git commit -m "source file backup" && git push`，用于快速提交当前源码分支。

## 已观察到的注意点

- 主题菜单包含 `/about/` 与 `/link/`，但 `source/` 下暂未看到对应页面源文件；若未创建页面，线上可能为 404。
- `source/_posts` 中存在部分资源目录未发现同名 Markdown（如 `2025软考高级系统架构师记录/`、`MCP-Java-SDK-初探/`），可按需清理或补齐文章。
- 仓库已通过 `.gitignore` 忽略 `public/`、`node_modules/`、`.deploy*`、`db.json`，建议持续保持“源码分支不提交构建产物”的习惯。

## License

本仓库当前未在根目录声明独立 LICENSE 文件；如需开源分发，建议补充明确许可协议。
