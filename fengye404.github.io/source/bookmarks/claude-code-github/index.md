---
title: "GitHub - anthropics/claude-code"
date: 2026-04-12
comments: false
aside: false
---

> **原文链接：** [https://github.com/anthropics/claude-code](https://github.com/anthropics/claude-code)
> **作者：** Anthropic
> **收藏日期：** 2026-04-12

---

# GitHub - anthropics/claude-code: Claude Code is an agentic coding tool that lives in your terminal, understands your codebase, and helps you code faster by executing routine tasks, explaining complex code, and handling git workflows - all through natural language commands.

![Node.js](68747470733a2f2f696d672e736869656c64732e696f2f62616467652f4e-1a1273fb.svg) ![npm](68747470733a2f2f696d672e736869656c64732e696f2f6e706d2f762f40-02f7de20.svg)

Claude Code is an agentic coding tool that lives in your terminal, understands your codebase, and helps you code faster by executing routine tasks, explaining complex code, and handling git workflows -- all through natural language commands. Use it in your terminal, IDE, or tag @claude on Github.

**Learn more in the [official documentation](https://code.claude.com/docs/en/overview)**.

![demo.gif](demo-ce3555cc.gif)

## Get started

Note: Installation via npm is deprecated. Use one of the recommended methods below.

For more installation options, uninstall steps, and troubleshooting, see the [setup documentation](https://code.claude.com/docs/en/setup).

### Install Claude Code:

**MacOS/Linux (Recommended):**

```shell
curl -fsSL https://claude.ai/install.sh | bash
```

**Homebrew (MacOS/Linux):**

```shell
brew install --cask claude-code
```

**Windows (Recommended):**

```powershell
irm https://claude.ai/install.ps1 | iex
```

**WinGet (Windows):**

```powershell
winget install Anthropic.ClaudeCode
```

**NPM (Deprecated):**

```shell
npm install -g @anthropic-ai/claude-code
```

Then navigate to your project directory and run `claude`.

## Plugins

This repository includes several Claude Code plugins that extend functionality with custom commands and agents. See the [plugins directory](https://github.com/anthropics/claude-code/blob/main/plugins/README.md) for detailed documentation on available plugins.

## Reporting Bugs

Use the `/bug` command to report issues directly within Claude Code, or file a [GitHub issue](https://github.com/anthropics/claude-code/issues).

## Connect on Discord

Join the [Claude Developers Discord](https://anthropic.com/discord) to connect with other developers using Claude Code.

## Data collection, usage, and retention

When you use Claude Code, we collect feedback, which includes usage data (such as code acceptance or rejections), associated conversation data, and user feedback submitted via the `/bug` command.

### How we use your data

See our [data usage policies](https://code.claude.com/docs/en/data-usage).

### Privacy safeguards

We have implemented several safeguards to protect your data, including limited retention periods for sensitive information, restricted access to user session data, and clear policies against using feedback for model training.

For full details, please review our [Commercial Terms of Service](https://www.anthropic.com/legal/commercial-terms) and [Privacy Policy](https://www.anthropic.com/legal/privacy).

## Repository Stats

- **Stars:** 113k
- **Forks:** 18.9k
- **Watchers:** 705
- **Contributors:** 51

## Languages

- Shell 47.1%
- Python 29.2%
- TypeScript 17.7%
- PowerShell 4.1%
- Dockerfile 1.9%
