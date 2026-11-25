---
author: "ZQY-LD"
name: bili-transcript
description: "读 B 站内容的总入口：口播全文（`bili_summary` 或本地字幕/ASR）、画面与演示（`bili_vision` 抽帧 + OCR）、opus 图文，以及简介与评论区。当用户给出 B站 BV 号 / 视频链接 / b23.tv 短链 / opus 链接，问「这视频讲了什么」「演示了什么」「长什么样」「值不值得装」「怎么用」，或要总结、引用原话、核对时加载；先按正文第 1 节判要口播还是要画面，再选通道。**只用于** B 站（BV 号 / b23.tv / bilibili.com / opus）。**不用于**：YouTube、本地视频文件与「理解这段视频」这类通用请求（本机暂无专用技能；video-understand 已于 2026-11-24 卸载）、直播实时抓取、纯图片理解（走 bili-vision 或直接读图）。"
---

# B 站内容读取（插件通道 + 技能内脚本）

给出 BV 号、视频链接、b23.tv 短链或 opus 链接后，先判「要口播还是要画面」，再选通道。**不要临时写下载/转写/抓取脚本**：插件有 `bili_summary` 与 `bili_vision` 两个现成工具，技能里还有落盘脚本。

**范围**：只接 B 站（BV 号 / 视频 URL / b23.tv / opus）；YouTube、本地视频文件、直播实时抓取、纯图片理解不接。

## 1. 先判要什么（别默认全走口播）

| 用户要的 | 走哪条 | 判据 |
|---|---|---|
| 说了什么、观点、原话、论证 | **`bili_summary`**（口播首选：字幕优先，无字幕本地 ASR；不下载视频、不抽帧） | 答案在语音里，画面只是配角 |
| 要落盘、复用缓存、强制重转、opus 图文 | **`scripts\transcript.mjs`** | 需要 `source` 字段、cache 文件、`FORCE_ASR`，或是 `/opus/` 链接 |
| 界面怎么操作、演示了什么、长什么样、有没有坑 | **`bili_vision`**（`action=inspect`，帧 + OCR + 字幕） | 答案在图里；口播常说「像这样」 |
| 只要文字、不想花视觉 token | **`bili_vision policy=text`**，或 `bili_summary` | 明确说「转成文字 / 只要口播」 |
| 图文帖子、专栏 | opus 通道（`transcript.mjs`）或 `bilibili_article_*` | 给的是 `/opus/<id>` 或 `read/cv` 链接 |

**两边都要时**：先 `bili_vision` 拿画面骨架，再用 `bili_summary` / `transcript.mjs` 补口播细节。反过来做会漏「口播念了但重点在画面」的内容。

**别只凭口播回答画面问题**：2026-11-22 用户问一个插件「长什么样」，只看 ASR 只能得到一串功能名，分不清它是接管侧栏还是新开窗口——这种问题直接 `bili_vision`。

## 2. 三条通道

### 2.0 先设本机常量（同一个 PowerShell 会话里设一次）

```powershell
$node  = "$env:USERPROFILE\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe"
$skill = "$env:USERPROFILE\.agents\skills\bili-transcript"
$mcp   = "C:\deepseek\tools\bili-mcp"
$env:BILIBILI_COOKIE_FILE = "$mcp\cookie.json"
```

`node` 已在 PATH 时可直接写 `node`。换机器改这三行，别改命令主体。

### 2.1 `bili_summary`（口播首选）

- 参数只有 `target`（BV 号 / 视频 URL / b23 短链）和可选 `sessionData`；不接受 opus。
- 返回带时间戳的全文（实测形如 `[0.0-30.0s asr]`），来自 B站字幕或本地 ASR；**不下载视频、不抽帧，不能回答画面问题**。
- 适合「讲了什么 / 引用原话 / 快速总结」；2026-11-26 实测 402 秒视频返回 208 段带时间戳文本。
- 无字幕时会自动本地转写，比字幕慢；要 JSON、缓存、强制重转或 opus，走 2.3。

### 2.2 `bili_vision`（画面）

- 默认 `action=inspect`：把带真实时间戳的画面、字幕/转写、OCR 一起交给当前模型；**先整体看，细节不足再用 `start`/`end` + `gridSize=1` 补看**。
- 常用参数：`ask` 传用户的实际问题（用于选相关帧）；`maxVision` 默认 12；`gridSize` 1/4/9；`ocr=true`；`policy=auto|always|text`。
- `policy=text` 只取文本、跳过画面，适合「只要口播」；`action=plan` 只看预算与覆盖，`action=run` 才调用独立 API（额外成本，别默认用）。
- `maxTextTokens` 默认 12000；**实测传 600 / 1500 都报「maxTextTokens 超出范围」**，不要给小值示例。
- 返回里的 `text_source` 会注明文本来自 ASR 还是字幕，`transcript_path` 可当口播底稿。

### 2.3 `transcript.mjs`（落盘、缓存、opus、强制 ASR）

```powershell
# 视频：缓存 → B站字幕 → 无字幕自动 ASR
& $node "$skill\scripts\transcript.mjs" BV1v5n56QECK

# opus 图文
& $node "$skill\scripts\transcript.mjs" "https://www.bilibili.com/opus/1217261987358048261"
```

- 参数只认 BV 号、视频 URL、opus 链接；`av` 号会被 usage 拒绝（转法见 2.4）。
- 数据目录默认 `cwd\.bili-transcript`，可用 `BILI_READER_DATA` 覆盖；`BILI_MCP_DIR` 覆盖 bili-mcp 目录。
- 视频输出 JSON：`bvid / source / seconds / lines / cache / head`；`source` 四种：`cache`、`B站字幕`、`ASR base`、`ASR base (forced)`。**`seconds` 是本次耗时，不是视频时长**——判断完整性看 `lines` 与缓存 txt 最后一条时间戳。
- opus 输出 JSON：`kind / id / title / author / paragraphs / chars / pics / source / out / seconds / head`；正文落 `<数据目录>\opus\<id>.txt`，图片只统计数量不下载。
- 全文落 `<数据目录>\cache\<BV>.txt`，格式 `[mm:ss] 文本`（只有 ASR 是 `[mm:ss]`；字幕沿用 `[m:ss]`）；字幕通道通常 1–2 秒，ASR 全链路实测 402 秒视频约 1 分钟（两次 57–59.5 秒，含 360p 下载 + 抽音频 + base/CPU 转写）。
- `FORCE_ASR=1` 跳过字幕走 ASR，但**仍先读缓存**；要强制重转，先删对应的 `cache\<BV>.txt`。
- `FORCE_CPU=1` 强制 CPU；默认就是 `auto`（GPU 不可用自动回 CPU）。

### 2.4 av 号与短链

- **av 号**：先用 API 换 BV，再进脚本：

```powershell
(Invoke-RestMethod "https://api.bilibili.com/x/web-interface/view?aid=117462171459225").data.bvid
# → BV1v5n56QECK
```

- **短链**：用 `curl.exe`（PowerShell 里 `curl` 是 `Invoke-WebRequest` 的别名），展开后核对标题与时长：

```powershell
curl.exe -s -o NUL -w "%{url_effective}" -L "https://b23.tv/xxxxxx"
```

一条消息里同时给短链和 BV 号时，先展开短链、确认是不是同一条；不是就各看一遍，并在结论里逐个交代看没看。

## 3. 简介 + 评论区（评估类必读）

2026-11-02 用户要求：**评估类请求看 B站视频时，简介和评论区都要看**，不能只看字幕正文——只读字幕就给「值不值得装 / 有没有坑」的结论＝不完整。

标准流程（默认四个步骤都走，例外见本节末）：

1. **字幕/转写**——`bili_summary` 或 `transcript.mjs`，拿口播正文。
2. **简介**——`bilibili_video_info` 取 `desc` 全文。UP 主常把**插件链接、仓库地址、参数、勘误、补充说明**放在这里。
3. **评论区**——`bilibili_video_comments`（一次最多 25 条，`page` 可翻）。看三类：①纠错（「视频里说的 X 我实测是 Y」）；②补充（UP 漏讲的坑）；③真实口碑（尤其负面反馈与踩坑记录）。
4. **三者分开写**——结构化为「正文说了什么 / 简介补充了什么 / 评论区怎么说」，**不要把评论区观点混进正文当作者原话**；有明显反面意见单独标出。

```powershell
& $node "$mcp\client.mjs" bilibili_video_info '{"videoId":"BV1v5n56QECK"}'
& $node "$mcp\client.mjs" bilibili_video_comments '{"videoId":"BV1v5n56QECK","page":1}'
```

2026-11-26 实测：`client.mjs` 能拉起 22 个工具，`video_info` 返回标题/时长/简介/aid，`video_comments` 返回 9 条评论并带 `rpid`。**必须带 `BILIBILI_COOKIE_FILE`**（2.0 已设），否则 server 匿名启动、WBI 报 `code=-101`。

**例外（只有一种）**：用户明确只要「转成文字 / 把口播给我」时，跑完第 1 步就交付；只要涉及评估、推荐、决策，或问「讲了什么 / 靠不靠谱 / 值不值得装」，第 2–4 步必做。

## 4. 行为与依赖

**视频**：缓存命中 → 直接返回；否则 B站字幕（`bilibili_video_subtitle`，已登录，通常 1 秒）；无字幕 → yt-dlp 下 360p → `asr.py --device auto` → 写缓存。

**opus 图文**：PC UA fetch 页面 → 取 `window.__INITIAL_STATE__.detail.modules` → `MODULE_TYPE_CONTENT` 的 `paragraphs[].text.nodes[].word.words` → 写 `<数据目录>\opus\<id>.txt`。无需登录；图片只计数不下载。

**依赖**（缺了会怎样见 `DEPENDENCIES.md`）：

- `$mcp\node_modules\bilibili-mcp-server\dist\index.js`（字幕/简介/评论）；
- `$mcp\cookie.json`（登录态；`BILIBILI_COOKIE_FILE` 指它）；
- `~\.dsh\bili-vision-venv\Scripts\python.exe`（faster-whisper 1.2.1 + ctranslate2 + av + numpy + yt-dlp；可用 `BILI_VISION_PYTHON` 覆盖）；
- `C:\deepseek\tools\bin\ffmpeg.exe`（抽音频；`transcript.mjs` 里写死在 PATH 前）；
- `$node`（DSH 自带 Node v24.21.0）。

**GPU 不可用是默认状态**：venv 里没有 cublas/cudnn，`asr.py` 自动回 CPU；要 GPU 就装 `nvidia-cublas-cu12 nvidia-cudnn-cu12`（约 2 GB），不装也能跑。ASR 模型写死 `base` + `zh`（`transcript.mjs` 调用处），换模型改那里。

**ASR 脚本随技能走**：`scripts\asr.py` 先把音频解成 numpy 再喂 faster-whisper，绕开 `av.open(metadata_errors=...)` 的兼容错误。**转写成功后自动删下载的视频/音频/中间文件**，只留 `cache/`；失败时保留 `tmp\<BV>.ytdlp.err` 与 `.asr.err` 便于排查。不要为省时间改成「只下音频」：用户要求无字幕时下载视频（画面可留作取证）。

## 5. 什么时候停

- **ASR 两次结果都一样地空/短** → 停，换 `bili_vision` 读画面，别第三次重跑。
- **拿不到字幕且音频不可下** → 停，说明原因并给替代（读简介、评论区，或让用户提供文件）。
- **评论数远少于预期** → 拉 3–5 个相关视频聚合后还少，按现有样本下结论并注明样本量，不无限翻页。
- **平台风控（`-509` / 验证码 / 空 body）** → 停手，别继续手搓 HTTP；走现成 MCP（专栏 `bilibili_article_info`，评论 `bilibili_video_comments`）。

## 6. 干完怎么算对（验收）

- **字幕/转写拿到了**：有 `source`、`lines`、缓存路径；用缓存 txt 最后一条 `[mm:ss]` 对比 `bilibili_video_info` 的 `duration`，明显短就换 `bili_vision`，不反复重试。
- **简介与评论区一起看**：发布类视频的实质内容常在简介给的仓库里；评论区的纠错与补充要写进总结。
- **错字与不可还原的词要标出来**：自动字幕的专有名词错误不要当事实转述，拿不准的标「字幕疑似 X」。
- **画面问题有帧作证**：回答「长什么样 / 演示了什么」时，引用 `bili_vision` 的时间戳或帧，不靠口播猜。

## 7. 排障

- **无字幕 / 转写为空**：先看 `tmp\<BV>.ytdlp.err` 与 `.asr.err`，再判「没人声」还是「下载不全」；两个已复现样本见 `evidence\asr-cases.md`。
- **短视频只返回 1 行**：先去 `bilibili_video_info` 查真实时长；缓存 txt 只有标题行＝下载不全或音频为空，删缓存 + `FORCE_ASR=1` 只重试一次，仍空就换 `bili_vision`。
- **GPU 崩（`0xC0000409`、无 traceback）**：`FORCE_CPU=1` 重跑。
- **`-101` / WBI 报错**：cookie 过期，`client.mjs bilibili_refresh_cookie` 或重新扫码；确认 `BILIBILI_COOKIE_FILE` 指对。
- **MCP 工具数会变**（2026-11-26 实测 22，历史上出现过 31）：写代码前先 `client.mjs list`；`bilibili_video_info` 的参数是 `videoId`，不是 `bvid`。
- **opus 抓不到**：报「页面没有 `__INITIAL_STATE__`（可能被风控/改版）」时，改用 `bilibili_article_info`（cvid 传**数字**）或让用户打开页面；专栏标题可能挂羊头，以正文为准。
- **`bili_summary` 不可用**：直接退到 `transcript.mjs`，字幕通道同样走 bili-mcp。

## 8. 附录：路径约定（跨机器可用）

| 符号 | 含义 | 作者机器实例 | 通用写法 |
|---|---|---|---|
| `DSH_HOME` | DSH 数据根 | `C:\Users\ZQY\.dsh` | `%USERPROFILE%\.dsh`（或 `DSH_HOME`） |
| `SKILLS_DIR` | 用户技能目录 | `C:\Users\ZQY\.agents\skills` | `%USERPROFILE%\.agents\skills` |
| `NODE_BIN` | Node 可执行 | `DSH_HOME\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe` | DSH 自带运行时，或 PATH 里的 `node` |
| `BILI_MCP_DIR` | bili-mcp 目录 | `C:\deepseek\tools\bili-mcp` | 任选，用环境变量 `BILI_MCP_DIR` 覆盖 |
| `BILI_VISION_PYTHON` | ASR venv 的 python | `DSH_HOME\bili-vision-venv\Scripts\python.exe` | 任选，用环境变量覆盖 |
| `TOOLS_DIR` | 自建工具目录 | `C:\deepseek\tools` | 任选；ffmpeg 在 `TOOLS_DIR\bin` |

换机器三步：①确认 `DSH_HOME`、`SKILLS_DIR`、`NODE_BIN`；②设 `BILI_MCP_DIR` 与 `BILI_VISION_PYTHON`；③ffmpeg 不在 `C:\deepseek\tools\bin` 时改 `scripts\transcript.mjs` 里拼 PATH 的那一行。其余判据（命令、字段、报错串）与路径无关。
