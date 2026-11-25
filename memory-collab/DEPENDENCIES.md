# 依赖清单（memory-collab）

> 路径符号含义见 `SKILL.md` 附录「路径约定」；本文件只写「缺了什么会坏」。

## 必需：meow-mind 插件

| 项 | 值 | 缺了会怎样 |
|---|---|---|
| 插件本体 | `meow-mind` **0.1.2**（源码 `$WORK_DIR\meow-mind`，profile 里按 `file:` 装） | `memory_*` 工具整片 unknown，本技能所有流程都跑不了 |
| 工作区库 | `<cwd>\.dsh-mind\memory.db`（跟着会话 cwd 走） | 本工作区的记忆读不到 |
| 全局库 | `<globalDir>\memory.db`，本机默认 `%USERPROFILE%\.dsh-mind-global`（插件里的常量 `DEFAULT_GLOBAL_DIR` 写死为 `C:/deepseek/.dsh-mind-global`） | 跨工作区准则与样板读不到 |
| 信箱 | `<globalDir>\mailbox\`（`inbox.md` + `archive\<YYYY-MM>.md`） | `memory_mail` 收发失效；`globalDir` 设空串时全局库与信箱一起停用 |
| 脚本 | `scripts\rebuild-index.mjs`，跑法见下 | 批量改正文后向量索引与正文不一致，检索大面积召回不到 |

**判据（分三样，别混）**：

- 库在不在 → `memory_health` 能返回条数、事件数、向量数与 `integrity`；
- 插件启用没有 → 工具整片 unknown 先查 `dsh.profile.bundles`（**装了 ≠ 启用**），再看 profile 的 `package.json` 有没有 `meow-mind`；
- 信箱通不通 → `memory_mail stats` 能返回未办数；它不归 `memory_health` 管。

## 脚本跑法（只此一种，别留第二套）

```powershell
$NODE_BIN = Join-Path $env:DSH_HOME 'dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe'
& $NODE_BIN (Join-Path $env:USERPROFILE '.agents\skills\memory-collab\scripts\rebuild-index.mjs')
& $NODE_BIN <同上脚本> '<库路径>'                  # 指定库
& $NODE_BIN <同上脚本> '<库路径>' '<meow-mind 目录>'  # 插件不在默认位置
```

用 runtime 的 node（要 `node:sqlite`），别用系统 node，也别再走 `ELECTRON_RUN_AS_NODE` + GUI 可执行文件那条老路。末行必须 `PASS`（细则见 `references\memory.md`「索引重建」）。

## 协作侧（内核自带，不是插件）

- 子代理：`subagent` / `subagent_fork` / `send_message` / `list_agents`
- 任务板：`team_task_*`
- 信箱：`memory_mail`（属 meow-mind，全局库没启用时一并失效）
- 这些缺了说明内核装配有问题，不是本技能的事——去看 `dsh` 技能的 `references/internals.md`
