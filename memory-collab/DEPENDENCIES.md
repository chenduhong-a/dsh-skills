# 依赖清单（memory-collab）

## 必需：meow-mind 插件

| 项 | 值 | 缺了会怎样 |
|---|---|---|
| 插件本体 | `meow-mind` 0.1.0（源码 `C:\deepseek\work\meow-mind`，profile 里 `file:` 装） | 22 个 `memory_*` 工具全部消失，本技能所有流程都跑不了 |
| 工作区库 | `C:\deepseek\work\.dsh-mind\memory.db`（跟着会话工作区走） | 本工作区的记忆读不到 |
| 全局库 | `C:\deepseek\.dsh-mind-global\memory.db`（`project='全局'` 落这里） | 跨工作区准则与样板读不到 |
| 信箱 | `C:\deepseek\.dsh-mind-global\mailbox\` | `memory_mail` 收发失效 |

判据：`memory_health` 能返回条数与 `integrity` 就说明这三个库都在；工具全 unknown 先查插件是否在 `dsh.profile.bundles` 里（装 != 启用）。

## 脚本

- `scripts\rebuild-index.mjs` —— 批量改正文、搬库、换 embedding 模型之后重算向量。**`memory_update` 只写正文，不重算向量**
- 跑法：本机 PATH 里没有 node，用 `$env:ELECTRON_RUN_AS_NODE='1'` + `C:\deepseek\官方\DeepSeek Harness.exe <脚本>`

## 协作侧

- 子代理：`subagent` / `subagent_fork` / `send_message` / `list_agents`（内核自带，不是插件）
- 任务板：`team_task_*`（内核自带）
- 这些缺了说明内核装配有问题，不是本技能的事（去看 `dsh` 技能的 `references/internals.md`）
