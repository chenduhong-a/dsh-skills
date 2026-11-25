---
author: "ZQY-LD"
name: memory-collab
description: 记忆维护与多代理协作二合一。当要写/改/合并/归档记忆、跑 dream 或记忆体检、修关键词语义、改 AGENTS.md 与准则文件、迁移记忆目录，问「记忆存在哪」「库里有多少条」「还占多少空间」这类库状态，或要查人格与画像、重建记忆索引、派子代理、切写域、抽查产物、做跨会话交接与信箱留痕时加载。核心口径：记忆只留坑与数字，步骤归技能。**不用于**：写技能文件本身（见 `skill-authoring`）、插件装卸与环境诊断（见 `dsh`）、跨会话代码协作（那走 `memory_mail` 信箱与 `C:\deepseek\上下文归档\` 的常规流程）。
---

# 记忆与协作

本文件只当路由：何时加载、读哪篇、两篇共用的铁律、停止条件与验收。细则在 `references/` 两篇，带日期的实测在 `evidence/measurements.md`。

## 使用约定（先看这里）

> **会话码自动补**（2026-11-21 起）：`memory_remember` / `memory_observe` / `memory_update` 会自动从 `exec.agent.session.header.id` 算码并补在正文末尾（`（码：XX-XXXXXXXX-XXXX）`），已带码不重复。写记忆时不用手打码；技能 `author` 字段仍要手写。

**每次收到 dream 任务（「meow-dream-group …」开头的提示）、或用户说「记忆体检 / 检查一下记忆库 / 整理记忆」时，第一步先 `skill` 加载本技能，再动手。**

原因：dream 由 meow-mind 插件注入、记忆体检是临时请求，**两条触发路径都不经过 `skill` 工具**——不主动加载，本技能就只是躺在磁盘上的文档，判据与流程全靠临场记忆（2026-11-19 发现并定规）。加载后再按第 0 节选篇。

## 0. 选篇

一主题一行，别一次读两篇：先按当前动作命中哪行。

| 当前要做的动作 | 读哪篇 |
|---|---|
| 写一条记忆：值不值得写、判该进技能还是记忆、判层、字段顺序、证据 | `references/memory.md` §2–§3 |
| 判两个库（工作区 / 全局）、看库位置与状态六态 | `references/memory.md` §1、§4 |
| 时间线：什么时候建事件 / 阶段 / 决定 / 性状，`env` 怎么填 | `references/memory.md` §6 |
| 合并 / 拆分 / 归档 / 按技能去重 / 批量精修正文 / 用户批改后的处置 | `references/memory.md` §7 |
| 记忆体检：四类问题怎么筛、报告怎么写 | `references/memory.md` §8 |
| 索引重建（含 `scripts/rebuild-index.mjs` 跑法与两条必抄口径） | `references/memory.md` §9 |
| 人格与画像：`persona_traits`、`user_profile` 的边界 | `references/memory.md` §5 |
| 改准则文件（`AGENTS.md` / 全局 `guidelines` 样板）与生效时机 | `references/memory.md` §10 |
| 迁移记忆目录 / 改 `globalDir` / 旧目录怎么退 | `references/memory.md` §11 |
| 常见错误速查 | `references/memory.md` §12 |
| 派不派子代理、任务书六样、先复用再新建 | `references/collab.md`「判据」「任务书六样」「先复用再新建」 |
| 切写域不重叠、并发上限、共享面归属 | `references/collab.md`「怎么切分」 |
| 抽查与验收（含子代理验收两条） | `references/collab.md`「验收与抽查」「子代理验收」 |
| 跨会话交接件与信箱留痕 | `references/collab.md`「跨会话交接」 |
| 查带日期的实测数字与案例（别在正文里找） | `evidence/measurements.md` |

> **索引重建有脚本**：批量改过正文、搬过库、或换过 embedding 模型之后跑 `scripts\rebuild-index.mjs`，用法与两条必抄口径在 `references/memory.md` §9。`memory_update` 只写正文，**不会**重算向量。

## 1. 两条线共用的铁律

1. **记忆只留「坑与数字、判据与指针」**，操作步骤归技能——同一份步骤写两处必然分叉。整理记忆时同步判去向、冲突以技能为准、批量整理先按技能去重（`references/memory.md` §7）。
2. **能拆给子代理的就拆**，主线只留结论；派活前先 `list_agents` 复用已有角色（`references/collab.md`）。
3. **子代理回执不可信**：声称「已写入」的，自己核字节数、行数、`##` 节数、frontmatter。
4. **常驻红线不进技能文件**：每条回复都命中的判据（弹卡正文、报告格式、转义）做按需加载＝制造「没加载就等于没写」的缺口。写作侧规矩见 `skill-authoring`。
5. **跨会话 / 共享面的改动当轮留痕**：写清改了哪条、影响面、回滚方式。影响全局的改动（插件、技能、全局准则、画像）完成后主动 `memory_mail post` 一封给「全体」——判据：别的会话不读这封就会按旧行为办事，就该发；纯文档错字、只影响本工作区、用户明说不用发的不必发。
6. **发信前后都要读信箱**（`memory_mail list`）：发之前看有没有人问过同一件事、有没有人回过你上一封，发之后看有没有新回信。只写不读＝自说自话（2026-11-21 用户原话：「发信的时候也要读信箱，别光写不读」）。

## 2. 什么时候停（停止条件）

- **两条记忆冲突且无法从证据判断谁对** → 停，问用户，不要自己选一条删另一条。
- **`memory_search` 连续换三个关键词都召回不到** → 停，去查 sqlite 原表或会话日志，不要在检索词上继续猜。
- **`memory_*` 工具整片 unknown** → 停，先查 `dsh.profile.bundles` 是否启用（**装了 ≠ 启用**）、profile 的 `package.json` 里有没有 `meow-mind`；别对着一个没挂载的库空跑整套流程。
- **cwd 不是目标工作区** → 停，先 `memory_home` 看两库路径与各层条数，确认改的是哪一本；别对着错的那本动手（库跟着 cwd 走，换目录就换库）。
- **dream 合并后条目内容对不上原文** → 停，从 `memory_versions` 回滚，不要手工修补。
- **子代理交付与任务书不符** → 停，重新派或自己补，不要接受「大致对」。

## 3. 干完怎么算对（验收）

- **写 / 改记忆、记忆体检**：①`memory_read` 回读，id、层、内容对得上；②字数自己复核（`[...str].length`——`rules`/`lesson` ≤250、`topic` ≤300、其余 ≤200）；③重读目标文件确认没有「（…」这类截断、没有 `TODO`/占位符；④报告带具体数字（条数、字数、归档数）与采集日期，不是「已完成」。
- **索引重建**：末行 `PASS`，且抽查一个「重建后才存在」的词能 `memory_search` 召回（口径在 `references/memory.md` §9）。
- **派子代理、跨会话交接**：自包含任务书 + 产物带具体数字（行数、字节、md5），条款在 `references/collab.md`「子代理验收」与「跨会话交接」。

## 附录：路径约定（跨机器可用）

本技能里的 `C:\deepseek\...` 与 `C:\Users\ZQY\...` 是作者机器上的实例路径；方法判据与下表配合，换台机器照样能跑：

| 符号 | 含义 | 作者机器实例 | 通用写法 |
|---|---|---|---|
| `DSH_HOME` | DSH 数据根 | `C:\Users\ZQY\.dsh` | `%USERPROFILE%\.dsh`（或环境变量 `DSH_HOME`） |
| `PROFILE_DIR` | 当前 profile | `DSH_HOME\profiles\desktop` | `DSH_HOME\profiles\<profile 名>` |
| `SKILLS_DIR` | 用户技能目录 | `C:\Users\ZQY\.agents\skills` | `%USERPROFILE%\.agents\skills` |
| `NODE_BIN` | Node 可执行 | `DSH_HOME\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe` | DSH 自带运行时，或 PATH 里的 `node` |
| `GLOBAL_DIR` | 全局库与信箱所在目录 | `C:\deepseek\.dsh-mind-global` | 插件常量默认值；配置项 `globalDir` 可覆盖，空串＝关闭 |
| `TOOLS_DIR` | 自建工具目录 | `C:\deepseek\tools` | 任选，固定后写回本表 |
| `PLUGINS_DIR` | 插件归档目录 | `C:\deepseek\插件` | 任选 |
| `WORK_DIR` | 工作区 | `C:\deepseek\work` | 任选 |
| `STUDY_DIR` | 学习资料 | `C:\deepseek\study` | 任选 |

换机器三步：①确认 `DSH_HOME`、`SKILLS_DIR`、`NODE_BIN`；②`scripts/` 里的常量在文件顶部，改成新路径再跑；③其余判据（版本号、报错串、行号、端口规则）与具体路径无关，通常不用改。
