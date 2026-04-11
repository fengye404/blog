---
title: "Launching Claude Managed Agents"
date: 2026-04-11
comments: false
aside: false
---

> **原文链接：** [https://x.com/RLanceMartin/status/2041927992986009773](https://x.com/RLanceMartin/status/2041927992986009773)
> **作者：** @RLanceMartin — Lance Martin
> **收藏日期：** 2026-04-11

---

**TL;DR** – Claude Managed Agents is a pre-built, configurable agent harness that runs in managed infrastructure. You define an agent as a template – tools, skills, files / repos, etc. The agent harness and the infrastructure are provided for you. The system is designed to keep pace with Claude's rapidly growing intelligence and support long horizon tasks.

![Image](/bookmarks/launching-claude-managed-agents/HFZdAn_bwAEOkmV-611f0d5e.jpg)

## Why Claude Managed Agents

The Claude Messages API is a direct gateway to the model: it accepts messages and returns content blocks. Agents built on the messages API use a harness to route Claude's tool calls to handlers and manage context. This poses a few challenges:

- **Harnesses need to keep up with Claude** – Agent harnesses encode assumptions about what Claude can't do. These assumptions grow stale as Claude gets more capable and can limit Claude's performance. Harnesses need to be continually updated to keep pace with Claude.
- **Claude is running for longer** – Claude's capability is growing, already exceeding over 10 human-hours of work on the METR benchmark. This puts pressure on the infrastructure around an agent: it needs to be safe, resilient to infrastructure failures that happen over long horizon tasks, and support scaling (e.g., to many agent teams).

Addressing these challenges is important because we expect future Claude to run over days, weeks, or months on humanity's greatest challenges. Claude Managed Agents is the next step: a system with the harness and managed infrastructure designed to support safe, reliable execution over the time-horizon that we expect Claude to work.

## How to get started

An easy way to onboard is to use the open source skill, which works out of the box in Claude Code:

```
$ claude update
$ claude
/claude-api managed-agents-onboarding
```

## Use cases

Some of the common patterns:

- **Event-triggered**: A service triggers the Managed Agent to do a task. For example, a system flags a bug and a managed agent writes the patch and opens the PR. No human in the loop between flag and action.

- **Scheduled**: Managed Agent is scheduled to do a task. For example, scheduled daily briefs of X or Github activity.

![Image](/bookmarks/launching-claude-managed-agents/HFZV93JaQAAbdHf-bcb6aebb.jpg)

- **Reactive / Multi-agent**: Claude working alongside users and other agents. For example, agents monitoring a shared state and collaborating toward a common goal.

![Image](/bookmarks/launching-claude-managed-agents/HFZXR5pakAA8c4K-8bfea2cd.jpg)

## Conclusion

Claude Managed Agents handles the agent harness and infrastructure for you, allowing for explorations on top of the agent as a new core primitive in the Claude API.
