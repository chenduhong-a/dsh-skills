---
author: "ZQY-LD"
name: bili-transcript
description: 读 B 站内容的总入口：口播全文（字幕优先、GPU ASR 兜底）、画面与演示（走 `bili_vision` 抽帧 + OCR）、opus 图文，以及简介与评论区。当用户给出 B站 BV 号 / 视频链接 / b23.tv 短链 / opus 链接，问「这视频讲了什么」「演示了什么」「长什么样」「值不值得装」「怎么用」，或要总结、引用原话、核对时加载；先按正文第 1 节判要口播还是要画面，再选通道。**只用于 B 站**（BV 号 / b23.tv / bilibili.com / opus）。**不用于**：YouTube、本地视频文件与「理解这段视频」这类通用请求（本机暂无专用技能；video-understand 已于 2026-11-24 卸载）、直播实时抓取、纯图片理解（走 bili-vision 或直接读图）。
whenToUse: The user pastes a bilibili.com link (video BV/URL, b23.tv short link, or /opus/<id>) and asks what it says, what it demonstrates, what it looks like, whether it is worth installing, how to use it, or asks to summarize/analyze it, or asks to read the content plus its comments.
---

# B站内容读取（transcript.mjs）

当用户给出 B站 视频链接/BV 号、或 opus 图文链接，需要「里面说了什么」时，用这个流程，不要自己临时写下载/转写/抓取脚本。

## 先判要什么（三选一，别默认全走口播）

| 用户要的 | 走哪条 | 判据 |
|---|---|---|
| 说了什么、观点、原话、论证 | 口播转写（下面的 `transcript.mjs`，字幕优先、ASR 兜底） | 答案在语音里，画面只是配角 |
| 界面怎么操作、演示了什么、长什么样、有没有坑 | `bili_vision`（`action=inspect`，抽帧 + 画面 OCR + 字幕一起给） | 答案在图里；口播常常只说「像这样」 |
| 图文帖子、专栏 | opus 通道（`/opus/<id>`）或 `bilibili_article_download` | 给的是 `/opus/` 或 `read/cv` 链接 |

**两边都要时**：先 `bili_vision` 拿画面骨架，再用 `transcript.mjs` 补口播细节。反过来做会漏「口播念了但重点在画面」的内容。

**别只凭口播回答画面问题**：2026-11-22 用户问一个插件「长什么样」，只看 ASR 只能得到一串功能名，分不清它是接管侧栏还是新开窗口——那种问题直接 `bili_vision`。

## 命令

```bat
node C:\deepseek\tools\bili-reader\transcript.mjs BV1v5n56QECK
node C:\deepseek\tools\bili-reader\transcript.mjs https://www.bilibili.com/opus/1217261987358048261
```

- 参数支持三类：BV 号、视频 URL、**opus 图文链接**（`/opus/<数字>`）。
- **技能内副本**：`node <本技能目录>\scripts\transcript.mjs <参数>`——与外部主脚本同一份代码，唯一差别是把 `here/../bili-mcp` 改成绝对路径并支持 `BILI_MCP_DIR` 覆盖。外部依赖（bili-mcp / cookie / venv / ffmpeg）与「为什么不全搬」见本目录 `DEPENDENCIES.md`。
- 运行目录不限；数据目录默认 `cwd\.bili-reader`，可用 `BILI_READER_DATA` 覆盖，**沙箱会话不需要提权**。

- **`av` 号不接受**：只认 BV / 视频 URL / opus，传 `av` 会被 usage 拒绝——先用 B站 API `x/web-interface/view?aid=<av>` 拿 `bvid` 再转（脚本已写进 `.bili-reader\avid.mjs`）。
- **短链可能指向另一条视频**：一条消息里同时给 `b23.tv` 短链和一个 BV 号时，先 `curl -s -o NUL -w "%{url_effective}" -L <短链>` 展开、核对标题与时长，再各看一遍并在结论里逐个交代看没看。

## 输出

- **视频**：JSON 摘要 `source`（B站字幕 / ASR base / cache）、`seconds`、`lines`、`cache`、`head`；全文在 `<数据目录>\cache\<BV号>.txt`，格式 `[mm:ss] 文本`。
- **opus**：JSON `{kind:"opus", title, author, paragraphs, chars, pics, out}`；正文在 `<数据目录>\opus\<id>.txt`。

## 行为

**视频**：
1. 缓存命中 → 直接返回；
2. B站 字幕优先：调 `C:\deepseek\tools\bili-mcp` 的 `bilibili_video_subtitle`（已登录，cookie 在 `cookie.json`），通常 1 秒；
3. 无字幕 → yt-dlp 下载 360p 视频 → 插件 venv 的 `asr.py --device auto`（GPU base）转写，再写缓存。

**opus 图文**：PC UA fetch 页面 → 取 `window.__INITIAL_STATE__.detail.modules` → `MODULE_TYPE_CONTENT` 的 `paragraphs[].text.nodes[].word.words`（文字嵌套在 `word.words`）→ 写 `<数据目录>\opus\<id>.txt`。无需登录；只取文字，图片只统计数量不下载。

## 开关（视频）

- `FORCE_ASR=1`：跳过字幕，强制走 ASR；注意脚本会先查缓存，要强制重转需先删 `<数据目录>\cache\<BV>.txt`。
- `FORCE_CPU=1`：强制 CPU 转写（GPU 不可用时自动回退）。

## 兜底与排障（无字幕 / ASR / 评论）

无字幕时三条路按顺序走，走不通就换路，不在同一条路上重试第三次。

1. **有字幕优先**：`bilibili_video_subtitle` 1–2 秒回，能拿到就不碰 ASR。
2. **无字幕走 ASR**：yt-dlp 360p → `asr.py --device auto`。返回 0 段**不等于工具坏**——2026-10-23 实测 BV1bNns6BEEA（9:58、有声，ffmpeg volumedetect mean -13.5dB），faster-whisper base/CPU 对 0–30s、120s、300–340s 三段全 0 段，实为纯 BGM/屏幕演示无人声。脚本只显示 ctranslate2 的 pkg_resources warning，**真错误在 `work\.bili-reader\tmp\<BV>.asr.err`**，先看它再判死活。
3. **评论/简介分开抓**：`bilibili_video_info` 拿标题/时长/简介 → `bilibili_video_comments` 拿热门评论（一次最多 25 条；单视频常不到 10 条，样本不够要跨 3–5 个视频聚合，rpid 记下来当门牌）→ `read_page` 读简介里的仓库/图文链接。发布类视频的实质内容常在仓库 README 里，不在口播里。

**短视频别信 ASR 的段数**：2026-11-10 处理 49 秒的 BV13W4J6kEHS，两次都只返回 1 行空字幕（`source=ASR base`，`seconds` 分别为 14 和 10），缓存 txt 只有标题行；删缓存 + `FORCE_ASR=1` 重跑结果一样——是 yt-dlp 只下到一小段或音频为空。判据：先用 `bilibili_video_info` 查 duration，`transcript.mjs` 返回的 seconds 明显短于时长＝下载不全，直接换 `bili_vision`（`target=BV`、`action=inspect`、`maxVision=10`），不要在 ASR 上反复重试。

**GPU 崩了就换 CPU**：GPU 路径失败（如 `0xC0000409`、无 traceback）时用 `FORCE_CPU=1` 重跑，可输出「ASR base / cpu」。

## 什么时候停（停止条件）

- **ASR 两次结果都一样地空/短** → 停，换 `bili_vision` 读画面，别第三次重跑。
- **拿不到字幕且音频不可下** → 停，向用户说明原因并给出替代（读简介、评论区、或让用户提供文件）。
- **评论数远少于预期** → 拉 3–5 个相关视频聚合后还少，就按现有样本下结论并注明样本量，不要无限翻页。
- **平台风控（`-509`／验证码／空 body）就停手换现成 MCP**：别继续手搓 HTTP——专栏走 `bilibili_article_info` + `bilibili_article_download`，评论走 `bilibili_video_comments`（一页 25 条），一次取全再判断。

## 干完怎么算对（验收）

- **字幕/转写拿到了**：返回 `source`（B站字幕 / ASR base）与行数、时长；`seconds` 明显短于 `duration` 就换 `bili_vision` 而不是反复重试。
- **简介与评论区一起看**：发布类视频的实质内容常在简介给的仓库里，评论区的纠错与补充要写进总结（2026-11-02 用户要求）。
- **错字与不可还原的词要标出来**：自动字幕的专有名词错误不要当事实转述，拿不准的标「字幕疑似 X」。

## 注意

- 需要 `~\.dsh\bili-vision-venv\Scripts\python.exe`（bili-vision 插件的独立 venv：faster-whisper 1.2.1 + ctranslate2 + av + numpy + yt-dlp 2026.11.23；作者机器 `C:\Users\ZQY\.dsh\bili-vision-venv`，510 MB）与 `TOOLS_DIR\bin` 里的 ffmpeg（作者机器 `C:\deepseek\tools\bin`）；不要重装/升级它们来「修」转写。
- **ASR 脚本随技能走**：`scripts\asr.py`（2026-11-24 从 `dsh-video-understand` 迁出，原文件在 `C:\deepseek\插件\patches\video-understand-0.5.2\asr.py`）。它把音频解成 numpy 数组再喂 faster-whisper——直接传文件路径会踩 `av.open(metadata_errors=...)` 的兼容错误（av 19 + faster-whisper 1.2.1）。
- **GPU 不可用是已知状态**：venv 里没有 nvidia cublas/cudnn（原来那套在 video-understand 的 venv 里，随插件卸载），`asr.py` 会自动回退 CPU；base 模型约 14× 实时（573 秒视频花 70 秒）。要用 GPU 就 `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`（约 2 GB）。
- 评论：用 `C:\deepseek\tools\bili-mcp` 的 `bilibili_video_comments`（带 `BILIBILI_COOKIE_FILE`）。
- **cookie / sessdata**：`C:\deepseek\tools\bili-mcp\cookie.json` 的 `sessdata` 键；`client.mjs` 必须带 `BILIBILI_COOKIE_FILE`（或 `$env:BILIBILI_SESSDATA`），否则 server 匿名启动、WBI 报 `code=-101`。cookie 是 2026-10-19 登录的（到 2026-11-17 已 28 天），没有固定失效期——每次自检真调一次只读接口验活，报 -101 就是过期。
- **MCP 工具数会变**：2026-11-14 实测只注册 22 个工具、2026-11-15 自检又回到 31 个且真调 OK。写代码前先 `tools/list` 确认工具名，别照旧假设；某些版本没有名为 `search` 的工具（报 `-32602 Tool not found`）。`bilibili_video_info` 的参数是 `videoId`，不是 `bvid`。
- **专栏**：`bilibili_article_info`（cvid 传**数字**，字符串会报 Expected number）返回标题/作者/字数/前 500 字预览；要看全文用 `bilibili_article_download`，落盘到 `<cwd>\bilibili-downloads\articles\<cvid>_<标题>\README.md`。专栏标题不可全信（可能挂羊头），以正文为准。裸 HTTP 的 read/cv 页面仍是 -509。
- 批量调用多个 MCP 工具：`node C:\deepseek\tools\bili-reader\batch.mjs jobs.json`，jobs 形如 `[{"tool":"bilibili_video_comments","args":{"videoId":"BV...","page":1},"limit":1800}]`；tmp 跟随 `<cwd>\.bili-reader\tmp`，沙箱免提权。
- 不要为省时间改成「只下音频」：用户明确要求无字幕时下载视频（画面可留作取证）。
- **转写成功后脚本会自动删掉下载的视频/音频/中间文件**，只保留 `cache/` 里的转写文本；失败时保留中间文件便于排查。用户 2026-10-20 要求：文案完整提取并核验无误后，不长期留视频占空间。
- **B 站一律走本技能**：`video-understand` 插件已于 2026-11-24 卸载（与 bili-vision 重叠），原先「两边都命中」的路由冲突随之消失；其它视频与本地文件本机暂无专用技能。

## 视频必读：简介 + 评论区（2026-11-02 用户要求）

用户 2026-11-02 明确要求：**评估类请求看 B站视频时，简介和评论区都要看**，不能只看字幕正文——只读字幕就给「值不值得装 / 有没有坑 / 怎么样」的结论＝不完整。

标准流程（默认四步都走，例外见本节末）：

1. **字幕/转写** —— 主入口 `transcript.mjs`，拿口播正文。
2. **简介** —— 带 `BILIBILI_COOKIE_FILE` 调 `bilibili_video_info`，取 `desc` 全文。UP 主常把**插件链接、仓库地址、参数、勘误、补充说明**放在这里；很多视频正文没讲清的细节只在简介里。
3. **评论区** —— `bilibili_video_comments`（一次最多 25 条，`page` 可翻）。看三类信息：①**纠错**（"视频里说的 X 我实测是 Y"）；②**补充**（UP 漏讲的坑）；③**真实口碑**（尤其负面反馈与踩坑记录）。视频里推荐的插件/工具，评论区往往有人踩过坑。
4. **三者分开写** —— 总结时结构化为「正文说了什么 / 简介补充了什么 / 评论区怎么说」，**不要把评论区观点混进正文当作者原话**；有明显反面意见要单独标出。

**例外（只有一种）**：用户明确只要「转成文字 / 把口播给我」时，跑完第 1 步就交付，简介与评论可以不看。**只要涉及评估、推荐、决策，或问「讲了什么 / 靠不靠谱 / 值不值得装」**，第 2–4 步必做——这三类里评论区往往比口播更可信（纠错、踩坑、负面反馈都在这儿）。这条同样适用于视频里推荐的任何工具或产品——先看 README/官方文档，再看评论区的真实反馈，别只信口播。

## 附录：路径约定（跨机器可用）

本技能里的 `C:\deepseek\...` 与 `C:\Users\ZQY\...` 是作者机器上的实例路径；方法判据与下表配合，换台机器照样能跑：

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

换机器三步：①确认 `DSH_HOME`、`SKILLS_DIR`、`NODE_BIN`；②`scripts/` 里的常量在文件顶部，改成新路径再跑；③其余判据（版本号、报错串、行号、端口规则）与具体路径无关，通常不用改。