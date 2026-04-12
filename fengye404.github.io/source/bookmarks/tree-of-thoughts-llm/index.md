---
title: "Tree of Thoughts: Deliberate Problem Solving with Large Language Models"
date: 2026-04-12
comments: false
aside: false
---

> **原文链接：** [https://arxiv.org/abs/2305.10601](https://arxiv.org/abs/2305.10601)
> **作者：** Shunyu Yao, Dian Yu, Jeffrey Zhao, Izhak Shafran, Thomas L. Griffiths, Yuan Cao, Karthik Narasimhan
> **收藏日期：** 2026-04-12

---

# Tree of Thoughts: Deliberate Problem Solving with Large Language Models

**arXiv:** [2305.10601](https://arxiv.org/abs/2305.10601) (NeurIPS 2023)

**Authors:** Shunyu Yao, Dian Yu, Jeffrey Zhao, Izhak Shafran, Thomas L. Griffiths, Yuan Cao, Karthik Narasimhan

## Abstract

Language models are increasingly being deployed for general problem solving across a wide range of tasks, but are still confined to token-level, left-to-right decision-making processes during inference. This means they can fall short in tasks that require exploration, strategic lookahead, or where initial decisions play a pivotal role. To surmount these challenges, we introduce a new framework for language model inference, **Tree of Thoughts (ToT)**, which generalizes over the popular Chain of Thought approach to prompting language models, and enables exploration over coherent units of text (thoughts) that serve as intermediate steps toward problem solving. ToT allows LMs to perform deliberate decision making by considering multiple different reasoning paths and self-evaluating choices to decide the next course of action, as well as looking ahead or backtracking when necessary to make global choices.

Our experiments show that ToT significantly enhances language models' problem-solving abilities on three novel tasks requiring non-trivial planning or search: Game of 24, Creative Writing, and Mini Crosswords. For instance, in Game of 24, while GPT-4 with chain-of-thought prompting only solved 4% of tasks, our method achieved a success rate of 74%.

**Code Repository:** [https://github.com/princeton-nlp/tree-of-thought-llm](https://github.com/princeton-nlp/tree-of-thought-llm)

## Key Highlights

- **Framework:** Tree of Thoughts (ToT) extends Chain-of-Thought prompting
- **Core Innovation:** Enables LMs to explore multiple reasoning paths and self-evaluate choices
- **Capabilities:** Supports lookahead and backtracking for global decision making
- **Results:** GPT-4 with ToT achieves 74% success on Game of 24 vs. 4% with CoT
- **Tasks Evaluated:** Game of 24, Creative Writing, Mini Crosswords
