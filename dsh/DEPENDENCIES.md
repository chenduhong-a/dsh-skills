# 依赖清单（dsh 技能 · 自检篇）

## 脚本
- `scripts/selfcheck.mjs` —— 自检主脚本（2026-11-22 实测 624 行，只用 Node 内置模块，零第三方依赖）
- `scripts/README.md` —— 用法与十项说明

## 外部依赖（本机固定路径）
| 依赖 | 路径 | 缺了会怎样 |
|---|---|---|
| DSH 运行时 node | `C:\Users\ZQY\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe` | 系统 node 也可，但 `node:sqlite` 需 22.5+ |
| profile | `C:\Users\ZQY\.dsh\profiles\desktop` | 依赖与 bundles 无法枚举 |
| 内核 CLI | `C:\deepseek\官方\resources\runtime\cli\bin\dsh.cmd` | 版本无法双证 |
| 记忆库 | 当前会话工作区 `.dsh-mind\memory.db`（不存在时退回 `C:\deepseek\work\.dsh-mind\memory.db`） | 记忆项无法统计 |
| 输出目录 | work 会话：`C:\deepseek\work\handover\selfcheck`；其它工作区：`<当前工作区>\work\handover\selfcheck`（各存各的，基线不互串） | 无法落档与差分 |

## 同步约定
自检脚本**只有一份**：本技能内 `scripts/selfcheck.mjs`。`C:\deepseek\tools\selfcheck\` 下的旧副本连同只指向它的 README 已于 2026-11-24 清掉，**不再维护双副本、也不再有 md5 同步要求**——改这一处就是全部。历史证据里出现的「两副本一致」只作当时的记录看。
