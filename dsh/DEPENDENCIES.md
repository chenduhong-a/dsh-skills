# 依赖清单（dsh 技能 · 自检篇）

## 脚本

- `scripts/selfcheck.mjs` —— 自检主脚本（2026-11-26 实测 895 行，只用 Node 内置模块 + `node:sqlite`，零第三方依赖）
- `scripts/studyhub-preset-patch.mjs`、`scripts/billion-ungate-patch.cjs` —— 两个补丁脚本（幂等；用法与重放时机见 `references/ops.md` 第 6 节）
- `scripts/README.md` —— 用法与十二项说明

## 外部依赖（符号写法见 `SKILL.md` 附录「路径约定」表）

| 依赖 | 通用位置 | 缺了会怎样 |
|---|---|---|
| DSH 运行时 node | `NODE_BIN`（`DSH_HOME\dsh-runtimes\...\node.exe`） | 系统 node 也可，但 `node:sqlite` 需 22.5+ |
| profile | `PROFILE_DIR` | 依赖与 bundles 无法枚举 |
| 内核 CLI | `DEPLOY_DIR\resources\runtime\cli\bin\dsh.cmd` | 版本无法双证 |
| 记忆库 | 当前会话工作区 `.dsh-mind\memory.db`（不存在时退回 `WORK_DIR\.dsh-mind\memory.db`） | 记忆项无法统计 |
| 输出目录 | `WORK_DIR\handover\selfcheck`（各工作区各存各的，基线不互串） | 无法落档与差分 |

作者机器实例：`DSH_HOME=C:\Users\ZQY\.dsh`、`DEPLOY_DIR=C:\deepseek\官方`、`WORK_DIR=C:\deepseek\work`。

## 同步约定

自检脚本**只有一份**：本技能内 `scripts/selfcheck.mjs`。`C:\deepseek\tools\selfcheck\` 下的旧副本连同只指向它的 README 已于 2026-11-24 清掉，**不再维护双份、也不做哈希比对**——改这一处就是全部。
