---
author: "ZQY-LD"
name: memory-collab
description: 记忆维护与多代理协作二合一。当要写/改/合并/归档记忆、跑 dream 或记忆体检、修关键词语义、改 AGENTS.md 与准则文件、迁移记忆目录，问「记忆存在哪」「库里有多少条」「还占多少空间」这类库状态，或要派子代理、切写域、抽查产物、做跨会话交接与留痕时加载。核心口径：记忆只留坑与数字，步骤归技能。**不用于**：写技能文件本身（见 `skill-authoring`）、插件装卸与环境诊断（见 `dsh`）、跨会话代码协作（那走 `memory_mail` 信箱与 `C:\deepseek\上下文归档\` 的常规流程）。
---

# 记忆与协作

本文件只当路由：何时加载、读哪篇、两篇共用的铁律与停止条件。细则全在 `references/` 两篇。

## 使用约定（先看这里）

> **会话码自动补**（2026-11-21 起）：`memory_remember` / `memory_observe` / `memory_update` 会自动从 `exec.agent.session.header.id` 算码并补在正文末尾（`（码：XX-XXXXXXXX-XXXX）`），已带码不重复。写记忆时不用手打码；技能 `author` 字段仍要手写。

**每次收到 dream 任务（「meow-dream-group …」开头的提示）、或用户说「记忆体检 / 检查一下记忆库 / 整理记忆」时，第一步先 `skill` 加载本技能，再动手。**

原因：dream 由 meow-mind 插件注入、记忆体检是临时请求，**两条触发路径都不经过 `skill` 工具**——不主动加载，本技能就只是躺在磁盘上的文档，判据与流程全靠临场记忆（2026-11-19 发现并定规）。加载后再按第 0 节选篇。

## 0. 选篇

| 情况 | 读哪篇 |
|---|---|
| 写一条怎么定层 / **什么时候写时间线（事件/阶段/决定）** / 合并拆分归档 / 体检流程 / dream / 库位置与六态 / 写作纪律 / AGENTS.md 何时生效 / 迁移红线 / 按技能去重 / 批量精修正文 / 用户批改后的处置 / **索引重建** | `references/memory.md` |
| 派不派子代理 / 任务书六样 / 切写域 / 抽查与验收 / 先复用再新建 / 跨会话交接与留痕 | `references/collab.md` |

> **索引重建有脚本**：批量改过正文、搬过库、或换过 embedding 模型之后，跑 `scripts\rebuild-index.mjs`（用法与两条必抄口径见 `references/memory.md`「索引重建」）。`memory_update` 只写正文，**不会**重算向量。

## 1. 两条线共用的铁律

1. **记忆只留「坑与数字、判据与指针」**，操作步骤归技能——同一份步骤写两处必然分叉。整理记忆时同步判去向、冲突以技能为准、批量整理先按技能去重，细则见 `references/memory.md`「按技能去重」与「写一条时的字段顺序」。
2. **能拆给子代理的就拆**，主线只留结论；派活前先 `list_agents` 复用已有角色。判据与做法见 `references/collab.md`「判据：这次自己干，还是派出去」与「先复用再新建」。
3. **子代理回执不可信**：声称「已写入」的，自己核字节数、行数、`##` 节数、frontmatter（细则见 `references/collab.md`「子代理验收」）。
4. **常驻红线不进技能文件**：每条回复都命中的判据（弹卡正文、报告格式、转义）做按需加载＝制造「没加载就等于没写」的缺口。写作侧规矩见 `skill-authoring`。
5. **跨会话 / 共享面的改动当轮留痕**：写清改了哪条、影响面、回滚方式。影响全局的改动（插件、技能、全局准则、画像）完成后主动发一封 `memory_mail post` 给「全体」——判据：别的会话不读这封就会按旧行为办事，就该发；纯文档错字、只影响本工作区、用户明说不用发的不必发。
6. **发信前后都要读信箱**（`memory_mail list`）：发之前看有没有人问过同一件事、有没有人回过你上一封，发之后看有没有新回信。只写不读＝自说自话（2026-11-21 用户原话：「发信的时候也要读信箱，别光写不读」）。

## 2. 什么时候停（停止条件）

- **两条记忆冲突且无法从证据判断谁对** → 停，问用户，不要自己选一条删另一条。
- **`memory_search` 连续换三个关键词都召回不到** → 停，去查 sqlite 原表或会话日志，不要在检索词上继续猜。
- **dream 合并后条目内容对不上原文** → 停，从 `memory_versions` 回滚，不要手工修补。
- **子代理交付与任务书不符** → 停，重新派或自己补，不要接受「大致对」。

## 3. 干完怎么算对（验收）

- 写/改记忆、记忆体检 → 条款在 `references/memory.md`「记忆验收」。
- 索引重建 → 末行 `PASS`，且抽查一个「重建后才存在」的词能 `memory_search` 召回（口径在 `references/memory.md`「索引重建」）。
- 派子代理、跨会话交接 → 条款在 `references/collab.md`「子代理验收」与「跨会话交接」。

## 附录：路径约定（跨机器可用）

本技能里的 `C:\deepseek\...` 与 `C:\Users\ZQY\...` 是作者机器上的实例路径；方法判据与下表配合，换台机器照样能跑：

| 符号 | 含义 | 作者机器实例 | 通用写法 |
|---|---|---|---|
| `DSH_HOME` | DSH 数据根 | `C:\Users\ZQY\.dsh` | `%USERPROFILE%\.dsh`（或环境变量 `DSH_HOME`） |
| `PROFILE_DIR` | 当前 profile | `DSH_HOME\profiles\desktop` | `DSH_HOME\profiles\<profile 名>` |
| `SKILLS_DIR` | 用户技能目录 | `C:\Users\ZQY\.agents\skills` | `%USERPROFILE%\.agents\skills` |
| `NODE_BIN` | Node 可执行 | `DSH_HOME\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe` | DSH 自带运行时，或 PATH 里的 `node` |
| `TOOLS_DIR` | 自建工具目录 | `C:\deepseek\tools` | 任选，固定后写回本表 |
| `PLUGINS_DIR` | 插件归档目录 | `C:\deepseek\插件` | 任选 |
| `WORK_DIR` | 工作区 | `C:\deepseek\work` | 任选 |
| `STUDY_DIR` | 学习资料 | `C:\deepseek\study` | 任选 |

换机器三步：①确认 `DSH_HOME`、`SKILLS_DIR`、`NODE_BIN`；②`scripts/` 里的常量在文件顶部，改成新路径再跑；③其余判据（版本号、报错串、行号、端口规则）与具体路径无关，通常不用改。
