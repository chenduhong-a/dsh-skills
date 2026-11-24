---
author: "ZQY-LD"
name: dsh
description: DSH 桌面版四合一手册——装升修卸、插件与工具开发、内核与现场取证、十二项自检。当用户要装/升级/卸载插件或 bundle、工具不见了、更新失败、面板提示新版、写 DSH 插件或给工具加参数、查某条会话当时说了什么、或直接说「自检」「体检」「检查环境」「升级后验收」时加载。先按第 0 节选篇再读 references。**边界**：问「有没有现成的插件、这功能能不能做」走 `official-plugins`，问「某个功能怎么实现、API 与设计规格是什么」走 `dsh-doc`；本技能管的是**动手**——装升卸、改配置、写插件、现场取证（日志 / GUI console / 会话记录）、自检。**不用于**：写技能文件（见 `skill-authoring`）、做视觉卡（见 `html-card`）、解析 PDF 与扫描件（见 `doc-parsing`）、读取 docx/pptx/xlsx（见 `doc-parsing` 的 Office 篇）、Office 文档生成（见 `univer` 系列）、商品挑选（见 `shopping-guide`）。
---

# DSH 桌面版手册（四合一）

本文件是路由 + 跨篇铁律；具体判据在 `references/` 四篇，按第 0 节选。

## 0. 选篇

| 情况 | 读哪篇 |
|---|---|
| 装 / 升 / 卸 / 工具消失 / 更新失败 / 版本判真伪 / 带补丁的包 / 内核更新善后 | `references/ops.md`（原 dsh-ops-playbook，40.6 KB，10 节） |
| 写插件 / 改别人的插件 / 加工具参数 / force 与缓存 / 产物卫生 / 改名收尾 | `references/plugin-dev.md`（17.3 KB，8 节） |
| 查服务注册 / 凭据与模型声明 / 会话日志 / GUI console / 上下文为何爆 | `references/internals.md`（12.8 KB，6 节） |
| 自检 / 体检 / 升级后验收 / 有没有新版 / 报告格式 | `references/selfcheck.md`（28 KB，十二项 + 四哨兵 + 四对账） |

**references 只放「怎么做 + 怎么判 + 什么不许」，案例证据在 `evidence/`**：四篇各有同名 evidence 文件，装的是带日期的实测记录、某次事故的字节数与报错原文、版本沿革——**执行时不用读**，只在「这个判据哪来的」「当时到底什么情况」时按节号去查。判据：**按需跨篇，不必全读**——装/升/卸看 ops（门控还要跨到 plugin-dev 的入口写法与 internals 的 asar 定位法）、写插件只看 plugin-dev、取证只看 internals、自检看 selfcheck（清理边界跨 ops 2.6）；只读本文件不够，一口气全读也没必要。

**先读判据再动手**：装升级类先读 ops 的「0 动手前五件事」，改代码类先读 plugin-dev 的「工具定义契约」。

## 1. 六条跨篇铁律

1. **装完必查 `deps` 与 `bundles`**：pnpm 换版可能把包从 `dsh.profile.bundles` 删掉——deps 还在、bundles 少一条，重启后工具面全消失。
   - 启用与否只看 `dsh.profile.bundles`：装配分三层（内核自带 → profile 的 `package.json` ＋ `node_modules` → bundles 启用清单），`dsh plugin --profile desktop add` 只保证装进 `node_modules`；有文件 ≠ 已启用。
2. **升级前备份 `profiles\desktop\package.json`**，升级后验版本号 + 工具面 + bundles 数。
3. **改了插件内文件或发布了新版本 → 必升 `package.json` 的 version**，否则作者重新发布会覆盖你的改动。
4. **带本地补丁的包，每次升级必重放补丁**：StudyHub 跑 `scripts/studyhub-preset-patch.mjs`（否则「学习模式」预设标红）；billion-context 跑 `scripts/billion-ungate-patch.cjs`（否则 `/compact` 又消失，文件 2589→2519 B）。
5. **自检即对账**：报告出来后对齐 `插件说明.txt`、技能引用、记忆库三者；报告格式见 selfcheck 第 3 节，对账五项见 5.1–5.5。
6. **回执与「成功」都要证**：工具说写成功、子代理说已落盘，都要用文件系统核字节 / 行数 / 节数。

## 2. 脚本（都在 `scripts/`）

| 脚本 | 用途 | 何时跑 |
|---|---|---|
| `selfcheck.mjs` | 十二项体检，`--quick` / `--full` / `--diff` / `--only 06,08`（只跑指定项，0.2 秒级，不落档不差分） | 用户说自检时 |
| `studyhub-preset-patch.mjs` | 修 StudyHub 自带 study 预设（3 处），`--check` 只报告 | 每次升 StudyHub 后 |
| `billion-ungate-patch.cjs` | 恢复 `/compact`（解除 compaction gate），`[--check]` | 每次升 billion-context 后 |
| `README.md` | 每个脚本的用法、要按本机改的常量（`SAFE_TO_CLEAN` / `PURPOSE` / `DO_NOT_TOUCH`）、返回码含义 | 脚本跑不起来时先读 |
| `DEPENDENCIES.md` | 脚本依赖的 profile、`dsh.cmd`、记忆库、落档目录在哪；缺了会怎样 | 换机器或换 profile 时先读 |

**路径口径**：正文里出现的 `TOOLS_DIR`（作者机器上是 `C:\deepseek\tools`）是历史副本位置；本技能 `scripts/` 下的才是随技能走的那份。两处都在时先改技能内这份、再同步工具副本（`selfcheck.mjs` 两副本 md5 必须一致；万一不一致，以 mtime 较新的一边为准并覆盖旧的一边）。

**另有两个说明文件**：`scripts/README.md`（每个脚本的用法、要按本机改的常量 `SAFE_TO_CLEAN`/`PURPOSE`/`DO_NOT_TOUCH`、返回码含义）与**技能根目录**的 `DEPENDENCIES.md`（脚本要用的 profile、`dsh.cmd`、记忆库、落档目录在哪——它不在 `scripts/` 里）。脚本跑不起来先读这两个，别从头猜。

## 3. 不许做的事

- 别把「每条回复都命中」的红线搬进技能文件——那些留在常驻注入层（弹卡正文、报告格式、尖括号与引号转义、字号跟随）。
- 别用 python-pptx / openpyxl / python-docx 处理 Office——那是 `univer` 系列技能的事。
- 别在没备份时删插件目录；别删 `file:` 依赖的 tgz 与 `link:` 依赖的源码目录。
- 别手改 `dsh.profile.bundles` 后不核对齐——0.2.2 起不再自动 reconcile。
- 别在热重载后立刻调新工具——热重载只重装装配表、不重新注册工具，要调新工具必须电源键完全退出重启；客户端那一半只改工具面不会生效。

## 4. 干完怎么算对（验收）

**拦法有强弱，按这个顺序落，能不靠文字就别靠文字**（从强到弱）：

1. **让它没地方犯**——一件事只留一处负责、删掉旧写法、合并要靠手同步的清单；写进脚本或结构里，想犯也没入口。
2. **让它一犯就报错**——`node --check`、白盒注册数、版本三判据、`--only` 断言；报错信息直接写「该怎么改」。
3. **让人一眼看见**——跑一次真宿主、贴返回结构、界面改动附截图；机器判不了的才用这档。
4. **只把需要判断的事写进 AGENTS.md / 本文件**——这是**最弱一档**，agent 跳过去什么都不会报错。今天大部分规矩都停在这档，能往上提就别留在这里。

**新增任何一道检查，都要拿这次真实犯过的错回放**：把错放回去必须报错，改回来必须通过。从来没报过错的检查等于没加。

**「本地做好了」不算做好了**：凡是要交给别人用的东西（推上远端的仓库、共享目录里的文件、给别人的报告、别人机器上要打开的东西），验收必须写清三样——**在哪**（哪台机器、什么路径或哪个 URL）、**怎么用**（打开方式或命令）、**对方能不能用**（缺权限、缺依赖、缺账号都不算能）。只在自己这台机器上跑通就报「已完成」，等于把验收标准写成了自己的环境。

按产物分的最小证据（每条都是可执行断言，不是「看一眼」）：

- **装 / 升 / 卸插件**：①`dsh plugin --profile <p> list` 里目标包在、版本对（**输出是 pnpm 依赖树，没有 `missingInBundles` 这类字段，别照着找**），且 `profiles\<p>\package.json` 的 `dsh.profile.bundles` 含该包；②`node_modules\<包名>\package.json` 版本一致；③宿主完全退出重启后新工具能真调一次并拿到结构正确的返回；④插件说明对应行已更新（版本 + 用途 + 日期）。四条全过才算完。
- **写插件**：①`node --check` 全过；②白盒测试里工具注册数与契约字段齐全；③装进临时 profile 后真实宿主能调用（headless 也行），失败路径降级不崩。
- **改脚本**：`node --check` + 跑一次最小用例（`--only <段>` 就是最小用例，别每次全量）。
- **改技能 md**：子代理按 description 触发一次确认命中；改完扫旧名。
- **自检报告**：按 `references/selfcheck.md` 第 3 节六条写满（插件逐个、MCP 分组、技能逐个、四件对账、使用统计单独一段 + 「这意味着什么」），不是只报数字。

**已知弱项，别自欺**：本机没有 lint / 类型检查 / git 提交钩子（`C:\deepseek\work` 下 0 个 `.git`）；`selfcheck.mjs` 是「全机体检」，替代不了「这次改动的验收」。所以第 2 档目前只有 `node --check` 和自检脚本可依赖，其余靠第 3 档人眼看。

## 5. 基线（2026-11-18）

内核 **0.2.2-rc.5** / Electron 44.7.0；profile **28 deps / 40 bundles**（2026-11-22 自检实测）；user 技能 **13 个**（本文件为其中之一）。**这行只当量级参考**：装卸任何插件都会变（11-19 装 `dsh-prompt-rewriter` 到 27/39，11-20 卸 vet 回 26/38，11-22 加 `dsh-a2ui` 与 `dsh-workspace-explorer` 到 28/40），报数前一律用 `dsh.cmd --version` + `dsh plugin --profile desktop list` 重核，别照抄。

## 附录：路径约定（跨机器可用）

本技能里的 `C:\deepseek\...` 与 `C:\Users\ZQY\...` 是作者机器上的实例路径；方法判据与下表配合，换台机器照样能跑：

| 符号 | 含义 | 作者机器实例 | 通用写法 |
|---|---|---|---|
| `DSH_HOME` | DSH 数据根 | `C:\Users\ZQY\.dsh` | `%USERPROFILE%\.dsh`（或环境变量 `DSH_HOME`） |
| `PROFILE_DIR` | 当前 profile | `DSH_HOME\profiles\desktop` | `DSH_HOME\profiles\<profile 名>` |
| `DEPLOY_DIR` | 桌面版程序本体 | `C:\deepseek\官方` | `resources\app.asar` 所在目录；`app-update.yml` 也在这一层。`dsh.cmd` = `DEPLOY_DIR\resources\runtime\cli\bin\dsh.cmd` |
| `SKILLS_DIR` | 用户技能目录 | `C:\Users\ZQY\.agents\skills` | `%USERPROFILE%\.agents\skills` |
| `NODE_BIN` | Node 可执行 | `DSH_HOME\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe` | DSH 自带运行时，或 PATH 里的 `node` |
| `TOOLS_DIR` | 自建工具目录 | `C:\deepseek\tools` | 任选，固定后写回本表 |
| `PLUGINS_DIR` | 插件归档目录 | `C:\deepseek\插件` | 任选 |
| `WORK_DIR` | 工作区 | `C:\deepseek\work` | 任选 |
| `STUDY_DIR` | 学习资料 | `C:\deepseek\study` | 任选 |

换机器三步：①确认 `DSH_HOME`、`SKILLS_DIR`、`NODE_BIN`；②`scripts/` 里的常量在文件顶部，改成新路径再跑；③其余判据（版本号、报错串、行号、端口规则）与具体路径无关，通常不用改。