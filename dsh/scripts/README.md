# selfcheck — DSH 完整自检

一个脚本顶掉十二项自检里的全部取数工作。你只说「自检」，我先跑它，再解读。

## 用法

```powershell
# 换机器先设环境变量（不设则用文件顶部常量里的作者默认值）
$env:SELFCHECK_WORK    = "C:\deepseek\work"      # 你的工作区根
$env:SELFCHECK_PLUGINS = "C:\deepseek\插件"        # 插件归档目录
$node = 'node'                                    # 或 DSH 自带 node.exe
& $node "$PSScriptRoot\selfcheck.mjs" --quick   # 快检 约 9 秒
& $node "$PSScriptRoot\selfcheck.mjs" --full    # 全检 约 14 秒
& $node "$PSScriptRoot\selfcheck.mjs" --diff    # 只看与上次的差分
```

- **快检**：内核 / 依赖 / 插件版本 / 记忆 / 服务端口 —— 日常或升级后立刻跑
- **全检**：在快检基础上加插件目录、B站 MCP、技能、工作区、HOME 体积、外部通道
- 结果同时打印并落档到 `<SELFCHECK_WORK>\handover\selfcheck\<时间>-<模式>.json`（默认 `C:\deepseek\work` 时），
  每次自动与上一份比对，输出：内核/依赖/bundles 变化、插件版本变化、体积涨落、记忆增减
- **`SELFCHECK_WORK` 改了会多套一层 `work`**：`WS !== WORK` 时落档是 `path.join(WS,'work','handover','selfcheck')`，两者相等才落 `WORK\handover\selfcheck`；报告路径出现 `work\work` 就是套了两层。

## 十二项 + 四对账

| 项 | 脚本取的数 | 判据 |
|---|---|---|
| 01 内核 | `dsh.cmd --version` ＋ exe FileVersion ＋ Electron 版本 | 两处内核读数一致 |
| 02 依赖 | profile 的 dependencies 与 `dsh.profile.bundles` | 声明的包全在 bundles 里；掉出＝工具面消失 |
| 03 插件 | 逐个包名 + 版本 + 安装来源 + 一句话用途 | 一个不漏，用途说得出 |
| 04 插件目录 | archives / backups / forks / patches / 活引用 clone 的体积与文件数 | 指出可清项 |
| 05 B站 MCP | 服务端在不在、cookie.json 最后写入时间、**起一次真 server 列工具并调 `bilibili_video_info`** | cookie 超过 14 天要实测；工具数应为 31 |
| 06 技能 | user 级清单 + 插件自带数量与分布 | 数量与 catalog 对得上 |
| 07 记忆 | active/all、七层分布、最长条目、wal 大小 | memory_search 能召回旧事实 |
| 08 工作区 | 总体积 + 各子目录 | 点名该清的临时目录 |
| 09 HOME | 各子树体积、GUI 端口 | 说清哪块最大、哪块可清、哪块动不得 |
| 10 外部通道 | QQ 插件与凭据、MinerU API、bsk daemon、worktree 残留、GUI 端口 | 断了你能先发现，我不该最后一个知道 |
| 11 更新检查 | 已并入 03：registry 查 npm latest、有 repository 的查 GitHub tag（jsdelivr），无 repository 标「自研」 | 四态「新 / 旧 → x.y.z / 自研 / 无 tag」；只比是否落后，本地领先也算「新」 |
| 12 使用统计 | 扫近 30 天会话日志：工具 schema 字符、技能目录字符、技能触发次数、插件调用次数、工具 top | 常驻开销两个数说清；30 天 0 次＝吃灰候选，但要标出来问用户，不直接判死 |

## 清理名单（不靠临场判断）

**可清**：插件 archives 里的旧 tgz、attachments 里已删会话的残留、`memory.db.bak`、
`logs` 里 7 天前的日志、`handover\selfcheck` 下 30 天前的 json。

**不可动**：`插件\dsh-raw-html-v2`（活引用 clone）、
`tools\mineru3-test\venv`（MinerU 运行时）、`tools\sci-venv`、`work\_pdftest`（用户拍板保留）。

## 冒烟：脚本证明不了的部分

脚本只能证明「进程内可验证」的事（记忆库能打开、内核命令能跑、端口能连）。
下面这些必须在对话里真调一次，否则「装了但调不动」查不出来：

1. `memory_search` 查一条旧事实（如「DSHM 平板 HoKit」）能召回
2. 本轮记忆注入横条可见
3. `univer_new` 建一个空文件并 `univer_status` 读回
   ⚠ 坑：建出来的 `.univer` 会被 univer 服务当场锁住，**删不掉也移不走**（句柄在 DSH 子进程里）。
   冒烟可以建在 `%TEMP%` 下；若已建在工作区，退出 DSH 后跑
   `C:\Users\ZQY\Downloads\clean-univer-temp.bat` 清理。
4. QQ 侧真发一条消息看有没有回
5. `schedule_list` 看定时任务还在不在

> B站 MCP 不在此列——`--full` 已自动起一次 stdio server、列工具并真调 `bilibili_video_info`。

这套流程同时固化成了技能：`C:\Users\ZQY\.agents\skills\dsh\SKILL.md`。

## 维护

- 新装插件时在 `PURPOSE` 表里补一行中文用途，否则报告里会显示包自带的英文描述
- 换版本后跑一次 `--full`，基线会自动更新
- **加项节奏**：先把最小版跑到能独立出结论（`--quick` 约 9 秒）再加检查项；同一套命令一周手打三次以上就该进脚本，别在临时命令里加第 N 个分支。
- 需要新的检查项就在 `external()` 或对应函数里加，输出段同步补一行；**会话日志的 zstd 是多帧拼接**，读它必须按 magic 逐帧解（见 `sessionLines()`），别用 `zstdDecompressSync` 一次性解整文件
- **加 `--only` 开关时每项产物各自赋值**：写成 `if (want('02')) out.deps = …`，别嵌进相邻项的 `if`；判据＝单跑一项，产物里出现别的项的默认值或空值就是嵌套了。
## 换机器要设的七项

脚本顶部常量全部「环境变量优先」，一个都不设时才是作者机器路径。换机器按需设：

| 环境变量 | 含义 | 不设时的默认 |
|---|---|---|
| `SELFCHECK_HOME` | 用户主目录 | `%USERPROFILE%` |
| `DSH_HOME` | DSH 数据根 | `%USERPROFILE%\.dsh` |
| `DSH_PROFILE` | profile 名 | `desktop` |
| `SELFCHECK_WORK` | 工作区根 | `C:\deepseek\work` |
| `SELFCHECK_PLUGINS` | 插件归档目录 | `C:\deepseek\插件` |
| `SELFCHECK_DSH_CMD` | 内核 cli 的 `dsh.cmd` | 作者机器绝对路径 |
| `SELFCHECK_EXE` | 桌面外壳 exe | 作者机器绝对路径 |

最小可用：只设 `SELFCHECK_WORK` 与 `SELFCHECK_PLUGINS` 就能跑大部分检查；第 01/02 项（内核版本）需要 `SELFCHECK_DSH_CMD` 或 `SELFCHECK_EXE` 至少一个。