---
author: "ZQY-LD"
name: dsh
description: DSH 桌面版四合一手册——装升修卸、插件与工具开发、内核与现场取证、十二项自检。当用户要装/升级/卸载插件或 bundle、工具不见了、更新失败、面板提示新版、写 DSH 插件或给工具加参数、给自研插件做全量缺陷测试（四片分法）、审读别人写的插件找缺陷、给测试 agent 写任务书、查某条会话当时说了什么、或直接说「自检」「体检」「检查环境」「升级后验收」时加载。先按第 0 节选篇再读 references。**边界**：问「有没有现成的插件、这功能能不能做」走 `official-plugins`，问「某个功能怎么实现、API 与设计规格是什么」走 `dsh-doc`；本技能管的是**动手**——装升卸、改配置、写插件、现场取证（日志 / GUI console / 会话记录）、自检。**不用于**：写技能文件（见 `skill-authoring`）、做视觉卡（见 `html-card`）、解析 PDF 与扫描件（见 `doc-parsing`）、读取 docx/pptx/xlsx（见 `doc-parsing` 的 Office 篇）、Office 文档生成（见 `univer` 系列）、商品挑选（见 `shopping-guide`）。
---

# DSH 桌面版手册（四合一）

> **适用范围：Windows 桌面版 DSH。** 本文的路径与命令都以 `C:\deepseek\官方`、profile `~\.dsh\profiles\desktop`、`dsh.cmd` 为准。**DSHM 端是另一套**——装配、命令（`install-queue` / `cores` / `exec`）与目录结构都不同，本文在那边不成立（2026-11-24 记）。

本文件是路由 + 跨篇铁律；具体判据在 `references/` 四篇，按第 0 节选。

**边界（与 description 的「不用于」同口径）**：写技能文件 → `skill-authoring`；视觉卡 → `html-card`；PDF / 扫描件 → `doc-parsing`；docx / pptx / xlsx 读取 → `doc-parsing` 的 Office 篇；Office 生成 → `univer` 系列；商品挑选 → `shopping-guide`；问现成插件与内核 API 规格 → `official-plugins` / `dsh-doc`。

## 0. 选篇

| 情况 | 读哪篇 |
|---|---|
| 装 / 升 / 卸 / 工具消失 / 更新失败 / 版本判真伪 / 带补丁的包 / 内核更新善后 | `references/ops.md`（操作流程 + 判据） |
| 写插件 / 改别人的插件 / 加工具参数 / force 与缓存 / 产物卫生 / 改名收尾 / 全量缺陷测试（四片分法） | `references/plugin-dev.md`（作者手册） |
| 查服务注册 / 凭据与模型声明 / 会话日志 / GUI console / 上下文为何爆 | `references/internals.md`（只取证不装不修） |
| 自检 / 体检 / 升级后验收 / 有没有新版 / 报告格式 | `references/selfcheck.md`（十二项 + 四哨兵 + 对账） |

**症状索引**（不知道读哪篇时先看这里）：`unknown tool` / 装了没生效 → `plugin-dev.md` §1.1 + `ops.md` §3；面板红点 / 提示新版 → `selfcheck.md` §4、§5.4；更新失败 / `Host did not complete graceful teardown` → `ops.md` §4；会话日志坏了 / 回答显示两遍 → `internals.md` §3；上下文 400 / 超限 → `internals.md` §5。

**references 只放「怎么做 + 怎么判 + 什么不许」，案例证据在 `evidence/`**：四篇各有同名 evidence 文件，装的是带日期的实测记录、某次事故的字节数与报错原文、版本沿革——**执行时不用读**，只在「这个判据哪来的」「当时到底什么情况」时按节号去查。判据：**按需跨篇，不必全读**——装/升/卸看 ops（门控还要跨到 plugin-dev 的入口写法与 internals 的 asar 定位法）、写插件只看 plugin-dev、取证只看 internals、自检看 selfcheck（清理边界跨 ops 2.6）；只读本文件不够，一口气全读也没必要。

**先读判据再动手**：装升级类先读 ops 的「0 动手前五件事」，改代码类先读 plugin-dev 的「工具定义契约」。

## 1. 六条跨篇铁律

1. **装完必查 `deps` 与 `bundles`**：pnpm 换版可能把包从 `dsh.profile.bundles` 删掉——deps 还在、bundles 少一条，重启后工具面全消失。
   - 启用与否只看 `dsh.profile.bundles`：装配分三层（内核自带 → profile 的 `package.json` ＋ `node_modules` → bundles 启用清单），`dsh plugin --profile desktop add` 只保证装进 `node_modules`；有文件 ≠ 已启用。
2. **升级前备份 `profiles\desktop\package.json`**，升级后验版本号 + 工具面 + bundles 数。
3. **改了插件内文件或发布了新版本 → 必升 `package.json` 的 version**，否则作者重新发布会覆盖你的改动。
4. **带本地补丁的包，每次升级必重放补丁**：StudyHub 跑 `scripts/studyhub-preset-patch.mjs`（否则「学习模式」预设标红）；billion-context 跑 `scripts/billion-ungate-patch.cjs`（否则 `/compact` 又消失，文件 2589→2519 B）。
5. **自检即对账**：报告出来后按 `references/selfcheck.md` 第 5 节把各处对齐到实况（插件说明、技能引用、记忆库）；报告格式见同篇第 3 节。
6. **回执与「成功」都要证**：工具说写成功、子代理说已落盘，都要用文件系统核字节 / 行数 / 节数。

## 2. 脚本（都在 `scripts/`）

| 脚本 | 用途 | 何时跑 |
|---|---|---|
| `selfcheck.mjs` | 十二项体检，`--quick` / `--full` / `--diff` / `--only 06,08`（只跑指定项，秒级，不落档不差分） | 用户说自检时 |
| `studyhub-preset-patch.mjs` | 修 StudyHub 自带 study 预设（3 处），`--check` 只报告 | 每次升 StudyHub 后 |
| `billion-ungate-patch.cjs` | 恢复 `/compact`（解除 compaction gate），`[--check]` | 每次升 billion-context 后 |

**路径口径**：正文里出现的 `TOOLS_DIR`（作者机器上是 `C:\deepseek\tools`）是历史副本位置；本技能 `scripts/` 下的才是现行版。**2026-11-24 起不再维护副本**，别恢复「两处同步」的旧做法。

**说明文件**：`scripts/README.md`（三个脚本的用法、环境变量、落档与清理名单）与技能根目录的 `DEPENDENCIES.md`（要用的 profile、`dsh.cmd`、记忆库、落档目录在哪）。脚本跑不起来先读这两个，别从头猜。

## 3. 不许做的事

- 别把「每条回复都命中」的红线搬进技能文件——那些留在常驻注入层（弹卡正文、报告格式、尖括号与引号转义、字号跟随）。
- 别用 python-pptx / openpyxl / python-docx 处理 Office——那是 `univer` 系列技能的事。
- 别在没备份时删插件目录；别删 `file:` 依赖的 tgz 与 `link:` 依赖的源码目录。
- 别手改 `dsh.profile.bundles` 后不核对齐——0.2.2 起不再自动 reconcile。
- 别在热重载后立刻调新工具：热重载只重装装配表、不重新注册工具——**改插件 JS 代码或新增工具定义，必须电源键完全退出重启**；只改技能 md、或只是把包补回 `dsh.profile.bundles`，热重载 / 刷新客户端即回（完整边界见 `references/ops.md` 第 3 节）。

## 4. 干完怎么算对（验收）

**拦法有强弱，按这个顺序落，能不靠文字就别靠文字**（从强到弱）：

1. **让它没地方犯**——一件事只留一处负责、删掉旧写法、合并要靠手同步的清单；写进脚本或结构里，想犯也没入口。
2. **让它一犯就报错**——`node --check`、白盒注册数、版本三判据、`--only` 断言；报错信息直接写「该怎么改」。
3. **让人一眼看见**——跑一次真宿主、贴返回结构、界面改动附截图；机器判不了的才用这档。
4. **只把需要判断的事写进 AGENTS.md / 本文件**——这是**最弱一档**，agent 跳过去什么都不会报错。今天大部分规矩都停在这档，能往上提就别留在这里。

**新增任何一道检查，都要拿这次真实犯过的错回放**：把错放回去必须报错，改回来必须通过。从来没报过错的检查等于没加。

**「本地做好了」不算做好了**：凡是要交给别人用的东西（推上远端的仓库、共享目录里的文件、给别人的报告、别人机器上要打开的东西），验收必须写清三样——**在哪**（哪台机器、什么路径或哪个 URL）、**怎么用**（打开方式或命令）、**对方能不能用**（缺权限、缺依赖、缺账号都不算能）。只在自己这台机器上跑通就报「已完成」，等于把验收标准写成了自己的环境。

按产物分的最小证据（每条都是可执行断言，不是「看一眼」）：

- **装 / 升 / 卸插件**：①`dsh plugin --profile <p> list` 里目标包在、版本对（**输出是 pnpm 依赖树，没有「缺 bundle」字段，别照着找**），且 `profiles\<p>\package.json` 的 `dsh.profile.bundles` 含该包；②`node_modules\<包名>\package.json` 版本一致；③宿主完全退出重启后新工具能真调一次并拿到结构正确的返回；④插件说明对应行已更新（版本 + 用途 + 日期）。四条全过才算完。
- **写插件**：①`node --check` 全过；②白盒测试里工具注册数与契约字段齐全；③装进临时 profile 后真实宿主能调用（headless 也行），失败路径降级不崩。
- **改脚本**：`node --check` + 跑一次最小用例（`--only <段>` 就是最小用例，别每次全量）。
- **改技能 md**：子代理按 description 触发一次确认命中；改完扫旧名。
- **自检报告**：按 `references/selfcheck.md` 第 3 节全部条目写满（插件逐个、MCP 分组、技能逐个、第 5 节对账、使用统计单独一段 + 「这意味着什么」），不是只报数字。

**已知弱项，别自欺**：本机没有 lint / 类型检查 / git 提交钩子（`C:\deepseek\work` 下 0 个 `.git`）；`selfcheck.mjs` 是「全机体检」，替代不了「这次改动的验收」。所以第 2 档目前只有 `node --check` 和自检脚本可依赖，其余靠第 3 档人眼看。

## 5. 基线（只当量级参考）

2026-11-26 实测：内核 **0.2.2-rc.5** / Electron 44.7.0；profile **26 deps / 37 bundles**；user 技能 **13 个**（本文件为其中之一）。装卸任何插件都会变，报数前一律重核，别照抄：

```powershell
$node = "$env:USERPROFILE\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe"
& $node -e "const j=require(process.env.USERPROFILE+'/.dsh/profiles/desktop/package.json');console.log(Object.keys(j.dependencies).length,'deps /',j.dsh.profile.bundles.length,'bundles')"
& "C:\deepseek\官方\resources\runtime\cli\bin\dsh.cmd" --version   # 作者机器；换机器换成 DEPLOY_DIR\resources\runtime\cli\bin\dsh.cmd
```

## 6. 什么时候停

- **用户没点头不动环境**：装、升、卸、清、改配置都要先给方案再执行；「要不要装」这类选型问题不是批准（`references/ops.md` §0）。
- **门控不过就停**：插件引用了内核已删的符号，写清缺什么、有没有替代包，别硬装（`references/ops.md` §1）。
- **同一动作失败两次就停**：换方案或回来问用户，别第三次照原样重试。

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
