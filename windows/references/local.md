---
name: windows-local
description: Windows 本机写脚本、改文件、跑诊断的防坑与验收清单——编码 BOM、PowerShell 引号与传参、Node 临时脚本后缀、文件锁与 CWD 占用、进程/设备/网络/浏览器诊断、Python venv 与原生崩溃、脚本报成功≠文件真变了。当任务要在这台 Windows 上落盘改文件、拼命令、查本机故障或验证 UI 时加载。
---

# Windows 本机操作手册

> 环境：Windows 11，`pwsh` 7.7.0 与 `powershell.exe` 5.1 并存，无 WSL，显卡 RTX 5070 Ti Laptop（sm_120）。括号内是教训编号。

## 判据

下面这些情况直接翻本篇：

- 要在这台机上写脚本、批量改文件、拼 PowerShell 命令；
- 报错看不懂：`EPERM`、`ENOENT`、中文乱码、`Unexpected token`、进程无 traceback 直接死；
- 本机能开、别的设备连不上；设备管理器不认某个设备；
- 脚本打印「成功」但文件/页面没变；
- 要调 `node`/`python` 却报命令不存在。

三条总则，后面所有条目都是它们的展开：

1. **能落盘就别拼命令行**：临时脚本写成文件再执行，验收也靠文件。
2. **先排除宿主假信号**：沙箱、回环、PATH、workdir 都会伪造「坏了」的结论。
3. **验收看产物，不看退出码**：退出码 0 与「文件真变了」是两件事。

本篇只管本机操作手法，不管 DSH 插件装升修，也不管 PDF/OCR 解析。

## 1. 脚本层（编码 / 引号 / 后缀）

### 1.1 编码：5.1 读写两头都会错（#89 · #161）

- 症状：中文变 `鐢ㄦ埛`；带 BOM 的 json 被读时报 `Unexpected token`，紧跟的引号里是一个不可见的 BOM 字符，`dsh plugin list` 报同一句；插件 `package.json` 被写出 BOM 后工具全变 unknown tool；node 读 `jobs.json` 同错。
- 判据：
  1. 读：5.1 的 `Get-Content`（含 `-Raw`）把无 BOM 的 UTF-8 按 GBK 解 → 中文乱码、中文 grep 假阴性；`.ps1` 同样按 GBK 解。
  2. 写：5.1 的 `Set-Content -Encoding UTF8` / `Out-File -Encoding UTF8` 会加 BOM。
  3. `pwsh` 7.7.0 起默认 UTF-8 且不写 BOM；但命令一旦走 `powershell.exe`，仍按 5.1 防。
- 处置：
  - 读中文：用 read 工具或 Python/Node 读；必须 PowerShell 时加 `-Encoding UTF8`。
  - 写中文：一律用 write/edit 工具落盘；脚本里用 node `fs.writeFileSync` 或 `[IO.File]::WriteAllText($p,$t,[Text.UTF8Encoding]::new($false))`。
  - `>` 重定向写出的是 UTF-16LE（夹 `\0`），接给 Python/Node 解析必失败——不要用它产出数据文件。
  - `.ps1` 保持纯 ASCII。

### 1.2 不要在 PowerShell 里拼代码（#107 · #173）

- 症状：替换整段失效；批量改 `插件说明.txt` 时 6 处替换只中 4 处，两份含反引号的行全落空；`python -c "…c.execute(f\"select count(*) from {t}\")…"` 报「无法将"*"项识别为 cmdlet」并 exit 1；双引号套 f-string 套 SQL，引号层级过深解析失败。
- 判据：
  1. 反引号在 PowerShell 里是转义符——双引号字符串与 here-string（`@"..."@`）都中招，会把后面的字符吞掉。
  2. 内联代码里出现 SQL、正则、嵌套引号，或 `$`（会被当变量展开）、`(` `)`、`|` 任意一项——直接落文件，不要试。
- 处置：
  - JS：用 write 写临时 `.mjs`/`.cjs` 再 `node` 执行；写完用 `Select-String` 或 node 复查命中数。
  - Python：写成 `$env:TEMP\xxx.py`，再 `& $py file.py` 跑。memory.db 完整性检查改成文件后一次通过。

### 1.3 Node 临时脚本的后缀（#117 · #122）

- 症状：`.mjs` 里 `require` 报 `not defined in ES module scope`；write 生成的 `.cjs` 报 `SyntaxError: Unexpected identifier`。
- 判据：`.mjs` 按 ESM 解析，不认 `require`；`.cjs` 里用模板字符串包一整段含反引号的 markdown，第一个反引号就把字符串提前终止。
- 处置：要用 `require` 就写 `.cjs`；正文含反引号时改用单引号 + 数组 `join` 换行，别用模板字符串包整段文本。

### 1.4 传参四坑（#161）

- 症状：
  1. 调原生 exe 时 JSON 参数被剥引号：`{"videoId":"BV..."}` 变成 `{videoId:BV...}`，程序解析失败。
  2. 自定义 `function Kill` 没生效，实际执行的是 `Stop-Process`。
  3. 给 `$home` 赋值报只读。
  4. `Start-Process -ArgumentList` 把含空格的路径拆开。
- 判据：PowerShell 会重写命令行——原生 exe 拿到的参数不保证带引号；别名优先于自定义函数；`$home`/`$Host` 等是只读自动变量；`-ArgumentList` 传数组会逐项拆。
- 处置：
  1. JSON 写文件，命令行传 `@路径`。
  2. 不要用与内置别名同名的函数。
  3. 换个变量名，别复用自动变量。
  4. 含空格路径不要走数组形式，改传单个命令行字符串。

### 1.5 .bat 必须纯 ASCII（#179）

- 症状：`'C:\...univer")' 不是内部或外部命令`、`'null' 不是内部或外部命令`，`del`/`2>nul`/`if exist` 全失去结构。
- 判据：cmd 解析 .bat 文件本身按系统 ANSI（本机 GBK/936）；`chcp 65001` 只改控制台输出代码页、不改变文件解析编码。UTF-8 中文注释被当 GBK 解读后，里面的 `"`、`&`、`(`、`)` 把命令拆碎。
- 处置：只用 ASCII 英文 `echo` 与注释、不要 `chcp`；结构用 `if not exist ... goto label` + `:label`，不要用 `&` 串联；写完用 `'' | cmd.exe /c "<bat>"` 实测一次（喂回车绕过 pause）。

## 2. 文件与进程（锁 / 占用 / CWD / 批量改）

### 2.1 删目录报 EPERM：先查占用进程的 CWD（#108）

- 症状：`fs.rmSync` 删目录报 EPERM，目录里的文件却能删。
- 判据：测试遗留的 node mock 服务、孤儿 python multiprocessing 子进程把工作目录指向该目录，锁住的是目录本身。
- 处置：查占用进程的 CWD，`Stop-Process` 掉它们再删。

### 2.2 workdir 不存在 → 误导性的 spawn ENOENT（#153）

- 症状：报 `spawn C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe ENOENT`，看起来像 shell 丢了；整条命令一行都不执行。
- 判据：真实原因是工具的 `workdir` 指向不存在的目录。
- 处置：先用默认 workdir `New-Item` 把目录建出来，再带 workdir 跑；再遇到这个 ENOENT 先 `Test-Path` 目标目录，不要怀疑 shell 或 PATH。

### 2.3 批量改文件：版本号不能全局替换（#119）

- 症状：把历史记录误改成「billion-context 0.1.215→0.1.215」，而原记录是 0.1.213→0.1.214。
- 判据：同一份文档里「历史条目」与「实装表」都有版本号，全局替换会一起改中。
- 处置：只改实装表对应行；改完 grep 历史区核对。
### 2.4 批量 CPU 计算把外壳拖死（explorer 重启 / 黑屏）
- 症状：node 跑 900 条 ONNX 嵌入、8 核满载数分钟后桌面黑屏；事件日志 Application Hang 1002「停止与 Windows 交互并已关闭」，Winlogon 记「外壳程序意外停止，userinit.exe 已重启」。
- 处置：分批并限线程——设 `OMP_NUM_THREADS` 或 onnxruntime 的 intra-op threads，别让单个批处理进程吃满全部核心。

## 3. 诊断通道（进程 / 设备 / 网络 / 浏览器）

### 3.1 常驻进程：DSH 里没有「脱离宿主存活」（#81 · #61）

- 症状：`cannot start an independent Windows daemon; the host may prohibit Job Object breakaway: 拒绝访问 (os error 5)`；`Register-ScheduledTask` 报 `Access is denied`（要管理员）。
- 判据：`Start-Process`、`-WindowStyle Hidden`、`wscript.exe` 中转（孙进程仍继承 Job）全都起不来。DSH 的 Job Object 不允许分离，反复试只是浪费。
- 处置：能成的只有三条——① 从 Explorer 双击 bat/vbs（父进程是 explorer，不在 DSH 的 Job 里）；② 登录启动项（Startup 文件夹，同样由 explorer 拉起）；③ `bsk daemon start --foreground` 跑在持久终端里。
- 附：daemon 默认 10 分钟空闲退出，要 `--daemon-idle 24h`；DSH 重启后 daemon 即失效，得手动重起。

### 3.2 设备诊断：沙箱里的假信号（#184）

- 症状：`Get-PnpDevice` 返回 0 台设备；`Get-CimInstance` 报 `HRESULT 0x80041003`；`Get-AppxPackage` 拒绝访问；`pnputil /scan-devices` 需管理员；`HKLM Enum\...\Properties` 键读不了。
- 判据：这些全是沙箱限制造成的假信号，不表示真没有设备、真坏了。
- 处置：只用可靠的两条——`pnputil /enum-devices`（可加 `/class` `/connected` 筛选）与读 Enum 基础值。

### 3.3 摄像头不在位：按硬件层往下走（#185）

- 症状：设备管理器显示摄像头 Disconnected。
- 判据：先动服务/隐私开关是无效功——用户按网上教程改过 FrameServer 启动类型和隐私开关，日志可见，但对「设备不在位」完全无效。
- 处置：硬件层 → 驱动层 → 服务层：① 热键（游戏本 Fn+F10）；② 真重启（快速启动开启时，「关机」不重新枚举 USB）；③ 卸载重装设备。

### 3.4 本机能连、别的设备连不上（#174）

- 症状：本机 `localhost` 返回 200，平板/别的机器打不开。
- 判据与处置（按序）：
  1. 确认服务绑的是 `0.0.0.0` 而不是 `127.0.0.1`：`Get-NetTCPConnection -State Listen`。
  2. 查防火墙：`Get-NetFirewallProfile` 看 `Enabled` 与 `DefaultInboundAction`（`NotConfigured` 等同阻止），再看该程序/端口有没有放行规则（当时 DSH 与 3081 一条都没有）。
  3. 本机回环不受防火墙约束，所以「本机 200、平板打不开」几乎一定是入站规则缺失或路由 AP 隔离。
- 绕开：无管理员权限时改用出站隧道（cloudflared 主动外连 443），不占入站端口。

### 3.5 上游 5xx：四步分清是谁的问题（#180）

- 症状：模型请求 500；DSH 自动重试 5 次、退避递增（「已重试模型请求 (3/5) · 1904 毫秒」），5 次全失败才报「本轮运行失败」。
- 判据（四步）：
  1. 先证本地没事：`Test-NetConnection api.deepseek.com -Port 443` 通 + 不带 key 请求 `https://api.deepseek.com/v1/models` 应返 401（返 401 即服务活着，是上游网关）。
  2. 看 `ProxyEnable=0`——残留 ProxyServer 配置不代表代理开着。
  3. 本地查不到 request_id：`~/.dsh/logs` 只有 hot-installer，`%APPDATA%\@deepseek-ai\dsh-desktop\logs` 只有 crash。
  4. 给官方留 request_id。
- 处置：**上游不稳时先发一句短结论**，细节等用户回了再补，长表格留到网络稳——长回复可能整轮丢失（诊断完准备写长回复时，本轮的模型请求自己撞上 500，用户只看到失败提示）。

### 3.6 GitHub API 配额（#205）

- 症状：连查几个仓库就 `403 rate limit exceeded`。
- 判据：未认证配额 60/小时，查几个仓库就没了。
- 处置：改从 npm registry 取 `dist.tarball` → 下载 tgz → `tar -xf` → 读 `package/README.md`；比 API 稳、不受限流，还能同时看 peer 与 engines。或直接 git clone 仓库。

### 3.7 浏览器：登录态边界（#47）

- 症状：同一个站，有时读到会员内容/动态/搜索历史词，有时弹登录墙或访客验证。
- 判据：bsk 用的是你 Chrome 的登录态——已登录站点（B站）能读会员内容；未登录站点被拦（微博热搜跳 `passport.weibo.com` 访客验证、知乎热榜弹验证码登录墙）；公开站点（GitHub trending）不受影响。B站首页部分推荐位被 AdGuard/AdBlock 屏蔽，读到「该内容被AdGuard/AdBlock类插件屏蔽」占位，要完整抓需加白名单。
- 处置：`bsk_session start` → `bsk_page navigate` → `bsk_inspect observe`（拿结构化 DOM/refs）→ 结束后 `bsk_session stop`；抓表格/列表用 `bsk_inspect extract`，留视觉证据用 `screenshot`。扩展断连报 `transport closed mid-call`，等扩展重连后**新开 session**，不要重复点击。

### 3.8 bsk CLI 的版本线与 daemon（#61）

- 症状：`unrecognized subcommand`；`the bsk CLI ("bsk") was not found`；`bsk status` 挂住不返回。
- 判据：CLI 版本线必须与插件一致（插件调 `bsk session request` 而 CLI 0.2.0 没有这个子命令）；新版只在 GitHub releases，npm 的 `browser-skill` 停在 0.2.0，直连不通走 ghproxy；0.4.0 起必须在 `cordis.patch.yml` 配 `bskPath`。
- 处置：`bsk status` 不可靠时，看 `~\.bsk\daemon.json` 的 pid/ws_port 与 daemon.log 判断死活。
### 3.9 沙箱里起浏览器：headless 一律崩
- 症状：Chrome/Edge `--headless` 启动即崩（mojo `platform_channel` 拒绝访问、`OpenProcess` 拒绝访问），pnpm 同时报 `spawn EPERM`。
- 判据：这类「拒绝访问＋EPERM」是沙箱禁子进程/管道，不是参数问题——停手，改用沙箱外既有服务或手动路径。

## 4. Python 与原生依赖

### 4.1 解释器一律写绝对路径（#175 · #197）

- 症状：`node` 报 CommandNotFoundException；`C:\Users\ZQY\AppData\Local\Programs\node` 目录根本不存在；`python`/`python3` 只命中 WindowsApps 的 Store 占位符，报 `Python was not found; run without arguments to install from the Microsoft Store`；openssl 也没有。
- 判据：PATH 会骗人——pwsh 与 niu bash 环境里都可能拿不到真解释器。别去装 Node，也别改 PATH。
- 处置：
  - node：先 `load_workspace_dependencies`，用它返回的 `C:\Users\ZQY\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe` 赋给变量再 `& $node 脚本`。
  - python：用 `C:/deepseek/tools/sci-venv/Scripts/python.exe` 的绝对路径。
  - sci-venv 是独立 venv（base 为运行时 Python 3.12.14，已装 numpy/scipy/matplotlib/pandas/lmfit，以 `pip list` 为准）；装包加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`，不装进 DSH 运行时。
  - 只需随机数/十六进制格式化：用 bash 内建 `$RANDOM` + `printf '%04X'`，不必去找解释器。

### 4.2 原生崩溃：没有 traceback 的进程死（#183 · #83）

- 症状 A（import 就崩）：`python -X faulthandler -c "import <pkg>"` 退出码 `-1073741819`(0xC0000005)，无 Python 栈，try/except 抓不到。
- 症状 B（GPU 计算崩）：进程 `0xC0000409`（`__fastfail`），没有任何 traceback；同一条 60 秒音频 CPU 18.5 秒正常、GPU 54 秒崩。
- 判据：
  - import 就崩＝包/运行时问题；import 通、调用才崩＝模型或数据问题。
  - 崩溃点无 traceback + 只在 GPU + 显卡比库新一两代 → 十有八九是 kernel 缺失。
- 处置 A（运行时 DLL）：比对 `System32\vcruntime140.dll`、`msvcp140.dll` 版本 vs 注册表 `HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64`——被旧程序覆盖时 System32 停在 14.00.24215.1 而注册表写 14.51（onnxruntime 1.31.1 崩溃的真凶）。修法：`VC_redist.x64.exe /repair /quiet /norestart`（退出码 3010＝成功待重启）。这类崩溃九成是运行时 DLL，不是包版本。
- 处置 B（算力）：① CPU/GPU 对照；② 短样本复现（别拿 10 分钟视频试——60 秒也崩，只是耗时长掩盖了）；③ 查算力 `nvidia-smi --query-gpu=name,compute_cap`，本机 12.0（sm_120，Blackwell）；④ 查库编译年代——`ctranslate2 4.5.0` 是 2024 年底 wheel，那时 Blackwell 未上市、没有 sm_120 kernel，跑到该架构就 `__fastfail`。换库版本，不是换算法。

### 4.3 venv 升包的两个必查冲突（#84）

- 症状：`pip install -U opencv-python` 把 `opencv-python-headless` 顶掉（原案例是 Indra 通道，2026-11-18 该通道已移除，但冲突模式通用）；装完 resolver 报 mpmath 1.4.1 与 sympy 1.14.0 冲突（sympy 要 <1.4）。
- 判据：`opencv-python` 与 `opencv-python-headless` 提供同名 `cv2`，只能留一个；mpmath 要回退 1.3.0。
- 处置：升 venv 时显式 `pip uninstall opencv-python` 再装 `opencv-python-headless`；mpmath 回退 1.3.0。大版本升级前先 `pip freeze` 到 `handover\backups\venvs-<日期>\`，否则 `pip install -U` 直接覆盖，崩了没法精确回滚。

## 5. 验收

### 5.1 脚本报「成功」≠ 文件真变了（#111）

- 症状：脚本打印成功，还打了 `bytes 7973 -> 8503`，文件其实一字未改。
- 判据：`lines.splice()` 删了行，却忘了 `s = lines.join('\n')` 同步回字符串，写回的是原始内容；字节数变大是头注释变长掩盖的；`lines after` 232 一行没变就该警觉。
- 处置：验收判据用**行数 + 残留关键词双查**。改对后是 232 → 148 → 145。

### 5.2 统计结果自相矛盾，先怀疑脚本（#133）

- 症状：数标签出现次数，`$s.Split('</div>')` 报 3 千多；同一份文件里 `</p>` 报 0 个，而 `<p` 报 4 个。
- 判据：`Split('</div>')` 会被 .NET 选成 `Split(char[])` 重载，按每个字符拆散；双引号里拼正则 `"</$t>"` 插值后匹配失败。
- 处置：`[IO.File]::ReadAllText` 读入后用 `IndexOf` 循环计数，或显式 `Split([string[]]'x', [StringSplitOptions]::None)`。校验结果自相矛盾时，先怀疑脚本，别急着怀疑文件。

### 5.3 UI 改动：截图看 1:1（#149）

- 症状：改了界面只能靠猜生效没生效；直接跑 `.ps1` 被执行策略以「AuthorizationManager 检查失败」拦下。
- 判据：Windows 下用 Add-Type + System.Drawing 的 `CopyFromScreen` 截前台窗口（`GetForegroundWindow` / `GetWindowRect`），存 PNG 再用 read_image 看，是可靠证据。
- 处置：把同样的代码内联进 pwsh 命令执行，别落成 .ps1；截图只覆盖窗口矩形——浮窗/独立窗口若在窗口外不会入镜。

### 5.4 出手前的四条核对

- 写文件：行数变了吗？关键词命中数对得上吗？中文没有变 `鐢ㄦ埛` 吗？
- 改文档：历史区有没有被全局替换误伤？（grep 历史区）
- 跑原生程序：有没有只看退出码、没看产物？
- 诊断：沙箱假信号、回环豁免、PATH 骗人、workdir 不存在——这四个宿主因素排除了吗？
- 临时产物：临时 `.mjs`/`.json`/探针文件用完删掉。
