---
name: dsh-internals
description: DSH 内核与现场取证手册——查「功能怎么实现 / 这条会话当时说了什么 / GUI 那个报错是什么 / 上下文账为何爆」时加载，覆盖服务注册与契约、凭据与模型声明、会话日志格式、GUI console 噪音、上下文计费五条取证路径。只取证不装不修。
---

# DSH 内核与现场取证

> 只回答「到底发生了什么」。装插件、升级内核、修坏掉的东西走 `references/ops.md`；写插件、改 preset 走 `references/plugin-dev.md`。本文件是执行口径：路径、命令、判据、红线。案例、实测数字与「当时以为是 X 结果是 Y」的排查过程在 `evidence/internals.md`（若按 `references/` + `evidence/` 目录装配，则为 `evidence/internals.md`）——执行时不必读，只在怀疑判据过时或需要交代依据时翻。

## 判据

先按问题分诊，别一上来就翻日志：

| 要回答的问题 | 第一判据 | 节 |
| --- | --- | --- |
| 某服务 / 某能力到底存不存在 | 源码 `provide` 或 grep，运行态实测 | 1 |
| 某模型能不能调、凭据对不对 | 直连上游 `/models`，按名字取钥 | 2 |
| 这条会话当时说了什么 / 为何重复 / 为何消失 | 会话日志；先按多帧解压 | 3 |
| GUI 那个红字是不是真错 | Electron console；先滤三类噪音 | 4 |
| 上下文为何超限 / 400 是不是体积问题 | `acp_status` 的 BILLED INPUT；请求投影 | 5 |

三条总纲：①**目录与 header 都是二手投影**——`listService` 是精选契约目录，`request/header` 是投影前的工具列表，都不等于全量注册表或真实请求体。②**会话日志只能由 DSH 自己写**——人可以读、可以在原始多帧备份上丢坏帧，但不能重写、不能重新分帧、不能 append。③**401 / 400 / 渲染错来自不同层**——凭据、工具投影、React 错误边界，证据来源完全不同。

## 1. 服务注册与内核源码

**症状**：`host Service.listService` 里找不到某服务；或要确认某能力在内核里到底有没有。**判据**：`listService` 是「精选契约目录」，**没列出来 ≠ 该服务不存在**（曾据此误判，依据见 `evidence/internals.md` 第 1 节）。**处置**（证据强度从高到低）：①源码——内核包里 `grep "provide("` 看服务名与注册点；②运行态——HTTP 路由探针或实际服务调用（200 / 405 / 404 各有含义）；③目录——`listService` 只用来查契约签名，不用来判存在性。

查内核源码：`app.asar` 是单文件明文包，没有逐文件路径可直接翻。用 `Buffer.indexOf(needle)` 定位服务名 / 错误串，再截前后窗口读上下文；**别信行号**——asar 里的偏移不是源文件行号，要按行号读就找对应的独立源码文件。

## 2. 凭据、模型目录与能力声明

**症状**：`/models` 和 `chat/completions` 同时 401、响应体为空；或自定义模型明明支持图片却被按纯文本处理。**判据（401）**：凭据要**按名字取**——`harness\.credentials.yaml` 里第一个 secret 不是 `DEEPSEEK_API_KEY`，按位置取第一条会两个接口双双 401 且响应体为空，极易误判成 key 失效（字符数与被取错的那条记录名见 `evidence/internals.md` 第 2 节）。

**处置**：①按文件里 `refs` 段的 `DEEPSEEK_API_KEY` 指向的记录取，不按顺序取。②判「某模型能不能调」直接打上游 `GET https://api.deepseek.com/models`——本地内核 catalog 是静态表、会滞后，不能当上游事实。③给自定义模型目录项补 `inputModalities` 必须显式写 `['text','image']`（落点＝该模型在 DSH 模型目录里的条目：GUI 模型设置里改，或改 `@deepseek-ai/dsh-llm-deepseek` 的 catalog 项；留空不会自动推断）；不写就按纯文本处理，图片走 `textOnlyPrice`、请求图像策略降级（`dsh-llm-deepseek` 的 `resolveRequestImagePolicy`，精确行号见 `evidence/internals.md` 第 2 节）。

## 3. 会话历史：定位、读原文、改日志

**症状**：要在旧会话里逐字回取一段话；侧栏标题找不到对应目录；同一条回答显示了两遍；或日志改完会话从列表里消失。

**3.1 存在哪、怎么找**：会话按 **cwd 分桶**，不按 profile：`$DSH_HOME\sessions\<workspace-slug>\session-<uuid>\`。侧栏标题不在会话日志里，在投影缓存 `%APPDATA%\dsh-desktop\harness\storages\session_projcache\sessions\<sessionId>.json`，直接 grep 形如 `"val": "标题"` 的字符串，比解压 zstd 快得多。按标题定位 / 删除：①在 `...\session_projcache\sessions\` 下 grep 标题，文件名即 `<sessionId>.json` → 会话 id；②判当前会话读 `profiles\<profile>\desktop-storage.json` 的 `dsh.sessions.current`，别误删正在写的；③删两处——会话目录 `$DSH_HOME\sessions\<cwd-slug>\session-<id>\`（含 v1 / v3 / v4 三代文件）+ 投影缓存 JSON；④复核：两个路径 `Test-Path` 都为 False；⑤侧栏可能短暂仍显示（客户端有会话顺序缓存），刷新页面即对账；**不要改 `desktop-storage.json`**，进程内存副本会覆盖手改。
**路径更正（2026-11-21 实测）**：投影缓存在 `$DSH_HOME\storages\session_projcache\sessions\`，`%APPDATA%\dsh-desktop\harness` 本机已不存在。
旧社区版才把数据硬编码在 `%APPDATA%\dsh-desktop\harness`，与本版 `DSH_HOME` 互不相认——换版本不继承，要手动搬。

**清探针会话**：探针同样按 cwd 落桶，删了 profile 与临时目录它还在。扫 `$DSH_HOME\sessions\` 下的日志帧，搜 `"probe ok"` / `"探针通过"` 等标记，**排除当前会话 id** 后再删目录；根治是跑探针时用独立工作目录（`Start-Process -WorkingDirectory`），让它落进另一个桶。

**3.2 读原文：先解多帧 zstd**。**判据**：`session.v4.jsonl.zstd` 是**多帧 zstd**，`zstdDecompressSync` 只解第一帧，第二帧起报 `Unknown frame descriptor`。**处置**：①按 magic `28 B5 2F FD`（`0xFD2FB528`）切帧，逐帧解压，再拼 JSONL 字节；②找 `assistant/message`，逐 part 打印 `content`——别只看界面；③查工具面时注意 `request/header` 只记投影前 active tools，不是实际请求体（见 5.2）。

最小切帧脚本（Node，`node:zlib` 自带 `zstdDecompressSync`）：

```js
const fs = require('fs'), zlib = require('zlib');
const inFile = process.argv[2], outFile = process.argv[3];
const b = fs.readFileSync(inFile), M = Buffer.from([0x28, 0xb5, 0x2f, 0xfd]);
const off = []; let i = 0;
while ((i = b.indexOf(M, i)) !== -1) { off.push(i); i += 4; }
const parts = off.map((s, k) => zlib.zstdDecompressSync(b.subarray(s, off[k + 1] ?? b.length)));
fs.writeFileSync(outFile, Buffer.concat(parts));
```

**3.3「一条回答显示两遍」先看 parts**：解多帧后找 `assistant/message`，打印 `content` 各 part——只有 `[reasoning, text]` 且 text 只有一份 → **渲染层重复**（流式预览残留 + 最终消息叠加），不是模型写了两份，别改生成习惯；reasoning 里出现完整正文草稿 → 才是生成层问题（判定样本见 `evidence/internals.md` 第 3 节）。

**3.4 改日志三条红线**。**判据**：内核 `SessionLogScanner` 按行严格校验 `event.seq === eventCount`（从 0 递增），典型错误 `released v2 row N has seq gap (expected X, got Y)`、`corrupt session log: invalid committed event at line N`。**红线**：①**不能整份重写成单个帧**——会话会从列表消失；②**不能重新分帧**（如每 200 行一帧）——即使 seq 连续 DSH 仍不认；③**不能 append 事件搬历史**（见 3.5）。**唯一正确修法**：恢复 **DSH 自己写出的原始多帧备份**，逐帧解压，只把自己插入的坏帧整帧丢弃，其余帧原样拼接写出；改前备份到 `work\handover\backups\`；运行中的会话不重读日志，改完要重启应用生效（帧数实测见 `evidence/internals.md` 第 3 节）。

**3.5 迁历史：写记忆库，不改日志**。**判据**：新会话自动继承的只有三样——记忆库（按工作区存 `<cwd>\.dsh-mind\memory.db`，同 cwd 就同一份）、磁盘上的文件 / 脚本 / 产物、profile / 全局级的插件、技能、配置；**对话历史不继承**（`sessions\<uuid>\` 按会话隔离，CLI 没有导出命令，只有 `--resume`）。**处置**：①不要改日志搬历史——append、整份重写、重新分帧三种改法都失败（seq 冲突或会话从列表消失）；②结论写进记忆库 + 写一页交接文件（如 `_relay\handover-<日期>.md`），新会话第一句让它读。

## 4. GUI 现场：console 与 BrowserSkill

**症状**：GUI 红字 / 白屏 / 消息渲染异常，需要 console 原始错误；或想用 BrowserSkill 直接打开 GUI 抓 console。**判据（BrowserSkill 为什么不行）**：BrowserSkill 连的是用户本机 Chrome（独立实例），抓不到 Electron GUI 的 console；用它打开 `http://127.0.0.1:<port>` 会返 **401** `dsh web authentication required`——GUI token 只在 Electron 启动时的地址栏 URL（`?token=`）里，不落盘（`~\.dsh\logs` 下只有一个空壳 dsh-hot-installer 目录，该插件 2026-11-22 已卸），进程命令行也搜不到。**处置**：①让用户在 GUI 窗口按 `Ctrl+Shift+I` → Console，复制红色错误（含 stack）——唯一直接来源；②或让用户发含 token 的完整 URL（形如 `http://127.0.0.1:<port>/?token=...`）——**带 token 的 URL 用 BrowserSkill 能打开**（鉴权只认 URL 参数），裸端口直接开才 401。

### 4.1 三类 console 噪音，只有第三类是真错

| 现象 | 判据 | 处置 |
| --- | --- | --- |
| `WebSocket connection to 'ws://127.0.0.1:9230/ingest' failed`（红屏刷） | 内核 experimental-inspector worker 的时序噪音 | `Get-NetTCPConnection -LocalPort 9230 -State Listen` 有监听即已恢复，清空 console |
| `inspector: globalThis.fetch is an accessor and cannot be observed safely`（常驻异常） | `dsh-experimental-inspector` 与 fetch 拦截不兼容的误报 | 功能正常就禁用该组件，别当健康判据 |
| `LaTeX-incompatible input … Unicode text character "（" used in math mode`（黄） | `$...$` 里混进中文标点（`（` `）` `，`）；KaTeX 只 warn 不炸 | 把中文标点留在公式外 |
| `[dsh-raw-html-v2] 渲染边界捕获`（红 + stack） | 真渲染异常（React 错误边界），只降级当前消息 | 在 console 过滤「渲染边界」，否则被前两类淹没 |

`dsh-raw-html-v2` 的 `VcpErrorBoundary` 只降级当前消息并打这条日志，不扩散到整页（实现细节见 `evidence/internals.md` 第 4 节）。
- **说「某个 UI 在哪」前先确认它此刻会渲染**：条件渲染组件（如任务面板，仅在存在任务时出现）只报位置会让人找不到，必须同时给「什么状态下出现」与临时造一个的步骤；用户说找不到先查条件，别重述位置。

## 5. 上下文账与请求体

**5.1 超限报错：先对账 BILLED INPUT**。**症状**：`maximum context length is <N> tokens. However, you requested <R> tokens (<M> in the messages, <K> in the completion)`。**判据**：单个会话历史堆爆 1M，不是模型总上下文突然变小；拆开看 messages + 输出预留。**先别认错**——用 `acp_status` 看 BILLED INPUT 确认是不是当前会话（实测有过报错来自别处长会话，原文见 `evidence/internals.md` 第 5 节）。输出预留 256K 是给 deepseek-flash 的 `max_tokens`，1M 扣掉它只剩 768K 给上下文。**处置**：①`/compact`，或开新会话；②别把整本 PDF、超大工具输出灌进同一会话；③本地日志查不到 `request_id`（`.dsh/logs` 只有 dsh-hot-installer 的旧目录（2026-11-22 该插件已卸），`@deepseek-ai\dsh-desktop\logs` 只有 crash），定位靠 `acp_status` 比对或直接问用户。

**5.2 `defer_loading` 400：根因在工具投影，不在体积**。**症状**：会话中途换过工具面（PTC ↔ 标准、装卸插件）后上游返回 400（与 `defer_loading` 有关）；改上下文大小、改 preset 名都无效。**判据**：根因在内核 `@deepseek-ai/dsh-llm` 的工具投影——①初始声明取会话最开始时那批 tools（无 `deferLoading`）；②历史里每次 `tool-addition` 的工具一律写成 `{...tool, deferLoading:true}`；③addition-only 再删掉当前不活跃的初始工具；④DeepSeek adapter 只发 `defer_loading:true`、从不发 false。于是会话中途工具面整体替换后，顶层 tools 无一非延迟 → 服务端 400；与上下文体积、preset 名都无关。`compress` 之所以有效，是因为 `tool-update` 消息被遮蔽后走回退分支，直接发原始 tools。**陷阱**：`request/header` 只记 active tools（投影前），**不能当实际请求体看**。**处置**：①新会话一开始就用目标模式，中途不换工具面；②旧会话用 `compress` 压到那条 `tool-update` 被遮蔽；③别打 asar 补丁——升级即覆盖。
