---
author: "ZQY-LD"
name: windows
description: "Windows 本机写脚本、改文件、跑诊断、开关系统代理的防坑手册。要在 C:\ 下落盘改文件、拼 PowerShell 命令、写 .bat/.ps1、跑 Node 临时脚本、查进程/端口/设备/网络/浏览器故障、磁盘空间不够或 C 盘满了、验证 UI，或需要临时翻墙访问 github.com 时加载。**不用于**：Linux / macOS 命令写法、DSH 插件的装卸与调试（见 `dsh`）、网站页面自动化（见 `browser-skill`）。"
---

# Windows 本机操作

本文件是最常用的红线；细节在 `references/` 两篇。

## 0. 选篇

| 情况 | 读哪篇 |
|---|---|
| 编码与 BOM / 引号与传参 / 文件锁与 CWD / 进程与设备 / Python venv 与原生崩溃 / UI 验证 | `references/local.md`（判据 + 脚本 / 文件进程 / 诊断 / Python / 验收） |
| 临时开系统代理访问 GitHub / raw.githubusercontent / ghproxy | `references/proxy.md`（三步开关 + 恢复与失败路径） |

## 1. 六条最高频红线

1. **别让 PowerShell 写 json**：PS 5.1 的 `Set-Content -Encoding UTF8` 会写 BOM，node 读报 `SyntaxError: Unexpected token '﻿'`（插件 package.json 中招 → 重启后全 unknown tool）。改 json 一律用 node `fs.writeFileSync`，或 `[IO.File]::WriteAllText($p,$t,[Text.UTF8Encoding]::new($false))`（后者要求 FullLanguage，见第 4 条）。
2. **`>` 重定向在 5.1 产出 UTF-16LE**；要给下游程序读的文本用 `Out-File -Encoding utf8NoBOM` 或干脆 node 写。
3. **`.mjs` 里不能用 `require`**；要么存成 `.cjs`，要么改 `import`。
4. **写文件用 write/edit 工具；只读沙箱下别用 `[IO.File]`**。`Set-Content` 会按系统代码页重编码，中文路径与内容都可能坏。**只读沙箱分支**：`$ExecutionContext.SessionState.LanguageMode` 返回 `ConstrainedLanguage`（或工具回执出现 `[sandbox: file access denied under read-only mode]`）时，`[IO.File]`、`Add-Type`、COM、反射全部不可用；读改用 `Get-Content` / `Test-Path` / `Select-String` / `Get-ChildItem`，落盘用 write/edit 工具或切 workspace-write，**不要重试同一种写法**（失败长相见 `local.md`「判据」）。**别做「`Get-Content -Raw` → `.Replace()` → `WriteAllText`」的整文件往返**——2026-11-15 实测只改一处措辞，同文件另一行的「第」字变成两个 U+FFFD（同一次写盘没动那行）。改中文优先 Python `io.open(path, encoding='utf-8')` 或 edit 工具；非用 PS 不可时，改完必须验 `(Get-Content -Raw).Contains([char]0xFFFD)` 为 False。
5. **PowerShell 内联写含引号/中文的 JS 容易解析失败**——写成 `.cjs` 文件再跑，别硬拼一行。
6. **删除前确认目标路径**：`Resolve-Path` / `Test-Path` 先看清打的是哪一条，删后复验「真的没了」（见 §3）。**本技能要问人的例外只有三类**：①永久删除（不是本次任务产生的临时产物）；②移出工作区（搬走、归档到别处）；③涉及别人正在用的（共享目录、别人进程占着的文件）。其余测试产物按 `AGENTS.md` §五「明确无用就当场删」，不用问。历史事实：`Remove-Item -Recurse -Force` 2026-11-12 被 CC Safety Net 拦下（终端提示删除被拒、文件还在）；**2026-11-21 复测三处都不拦**——workspace 内、workspace 外 `WORK_DIR`、技能目录全部直接删掉，`Get-ChildItem | Remove-Item` 也不拦。**「拦不住」意味着更危险，不是更方便**：被拦时不要换通道（python `shutil.rmtree`、`cmd /c rd` 都不是绕过理由），停下来问人；要给人看清单就先用 `-WhatIf`。别把「当时那套配置」写成永久规律。

## 2. 运行时基线

- node：`NODE_BIN`（DSH 自带运行时，见附录）；PATH 里的 `python` 可能是 0 KB 假 stub，别依赖裸命令名
- pwsh 7.7.0（Store 版）已装（2026-11-26 核实）；显式调 `powershell.exe` 的老脚本仍按 5.1 防
- ffmpeg：`TOOLS_DIR\bin\ffmpeg.exe`；LibreOffice：`C:\Program Files\LibreOffice\program\soffice.exe`（随安装位置变）
- `$home` 是只读自动变量，别拿来当自己的变量名

## 3. 干完怎么算对（验收）

写完或改完一个脚本/命令——**三条全过才算完**：①真跑一次并拿到预期输出（不是「看起来对」，是跑出来的）；②中文路径与中文内容没被重编码（`[IO.File]::ReadAllText` 回读一眼；只读沙箱改用 `Get-Content -Encoding UTF8`）；③失败路径有明确报错而不是静默返回空。

**删除类操作要复验「真的没了」**：`Remove-Item` 正常返回不代表文件消失；`Get-ChildItem | Select-Object -First N` 的截断还会让你看到「还剩几条」的假象。删完用 `Test-Path` 或重新列一次目录确认，删目录树尤其要。

**换解释器 / 换 venv 之后，`--help` 全绿不代表能跑**：2026-11-19 切新 venv，当时 18 个子命令 `--help` 全过（当前数量以 `--help` 实际输出为准），第一条实际命令就 `ModuleNotFoundError: pypdfium2`。按 import 清单补依赖，并把每个入口实执行一次最小真实用例——`--help` 只证明能 import 到 argparse。

诊断类任务——**两条**：①结论要有可复现的命令或日志行支撑（"可能是 X" 不算）；②排除项要写出来（查了什么、排除了什么），只报一个猜测等于没查。

## 4. 五个高频坑（本机实测，随版本/机器变）

- **cv2.imwrite 中文路径静默失败**：`cv2.imwrite(r"D:\中文\a.jpg", img)` 返回 False 但不抛异常，文件根本没生成。改 `ok, buf = cv2.imencode(".jpg", img)` 再 `open(path, "wb").write(buf.tobytes())`。
- **PowerShell `-f` 的 `{2:0.1}` 是 .NET 自定义格式串，不是「保留一位小数」**：`"{2:0.1} MB" -f $a,$b,$c` 会把 94.1 MB 印成 941 MB（`0.1` 是格式族不是小数位）。要格式化数字先 `[math]::Round($c,1)` 再传。
- **统计目录体积要 `-Force` 且必须带目标路径**：`Get-ChildItem -Path <目录> -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum` 默认跳过隐藏项与系统项，少算的部分能到几十 MB。看谁占得多按子目录排序：`Get-ChildItem <目录> -Directory -Force | ForEach-Object { [pscustomobject]@{ Name = $_.Name; MB = [math]::Round(((Get-ChildItem $_.FullName -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum / 1MB), 1) } } | Sort-Object MB -Descending | Select-Object -First 15`。
- **起长任务只有 `Start-Process` 能活过调用**（但不能脱离 DSH 宿主，见 `local.md` 3.1）：`& node ...`、`Start-Job`、`Register-ObjectEvent` 都在父进程退出时被带走。要 `Start-Process -FilePath $exe -ArgumentList $argv -PassThru -RedirectStandardOutput $log -RedirectStandardError $err -WindowStyle Hidden`。
- **端口被旧进程占着，改动看起来没生效**：先 `Get-NetTCPConnection -LocalPort <port> -State Listen | Select-Object OwningProcess` → `Stop-Process -Id <pid> -Force` → 重起再验。先看占用，再怀疑代码。

## 5. 诊断：先量再猜（磁盘为例）

进程 / 端口 / 文件是否存在与大小 / 事件日志 / 接口返回码。脚本报「成功」要用文件系统或接口复验一次——原生崩溃常常无 traceback，退出码也不能当判据。

### 5.1 磁盘空间（先证伪「满了」）

顺序别反：**先看 C: 到底还剩多少**，再谈清理。

```powershell
Get-PSDrive C | Select-Object @{n='UsedGiB';e={[math]::Round($_.Used/1GB,1)}}, @{n='FreeGiB';e={[math]::Round($_.Free/1GB,1)}}
```

- 剩余 > 20 GiB 时「磁盘满」基本不是原因，别为了清缓存浪费一轮；
- 真要紧的是**哪几个目录在涨**——按第 4 节的子目录排序命令递归求和再报，别只报一个总数；
- 清理边界与勿删清单在 `dsh` 技能的 `references/ops.md` 2.6（`%TEMP%\dsh-acl-locks`、插件 venv 里的 `nvidia` 包、凭据目录都别动）。

## 6. 代理

只在需要翻墙时开，三步在 `references/proxy.md`（改 HKCU 用户级，不动系统级默认）；Clash 刚启动时 GitHub API 会报 `unexpected EOF` / SSL 未就绪，等 10 秒、最多重试 4 次。node 进程的请求不读 WinINet，必须显式 `-Proxy http://127.0.0.1:7897` 或走 IWR。用完恢复原状（含清 `HTTP_PROXY` / `HTTPS_PROXY`）。

## 附录：路径约定（跨机器可用）

本技能里的 `C:\deepseek\...` 与 `C:\Users\ZQY\...` 是作者机器上的实例路径；方法判据与下表配合，换台机器照样能跑。**本表是本技能的唯一路径来源**；其它技能（`study-intake` / `doc-parsing`）的附录与它同构，换机器只改本表。

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

换机器三步：①确认 `DSH_HOME`、`SKILLS_DIR`、`NODE_BIN`；②正文与 `references/` 里的实例路径按本表替换（本技能没有 `scripts/`）；③其余判据（版本号、报错串、端口规则）与具体路径无关，通常不用改。
