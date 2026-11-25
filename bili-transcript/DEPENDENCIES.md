# 依赖清单（bili-transcript）

## 脚本（都在本技能 `scripts\` 下）

| 文件 | 行数 | 作用 |
|---|---|---|
| `scripts\transcript.mjs` | 218 | 视频：缓存 → B站字幕 → 无字幕 ASR；opus 图文抓取；输出 JSON + 落盘 txt |
| `scripts\asr.py` | 153 | faster-whisper 转写；先把音频解成 numpy 再喂模型，绕开 `av.open(metadata_errors=...)` 兼容错误 |

原外部 `tools` 下的读取器目录 **2026-11-25 已整块删除**；技能内这份是**现役入口**，改脚本只改这里。备份目录 `C:\deepseek\插件\backups\skills-20261118\bili-transcript\scripts\transcript.mjs` 是旧快照，别改错。`batch.mjs`、`opus-read.mjs`、`opus-probe.mjs` 随目录删除，不再有兄弟脚本。

## 外部依赖

| 依赖 | 路径 | 缺了会怎样 |
|---|---|---|
| bili-mcp 服务端 | `C:\deepseek\tools\bili-mcp\node_modules\bilibili-mcp-server\dist\index.js` | 字幕通道不可用，只能 yt-dlp + ASR；简介/评论/专栏也抓不到 |
| bili-mcp 客户端 | `C:\deepseek\tools\bili-mcp\client.mjs` | 无法直接调 `bilibili_video_info` / `bilibili_video_comments` 等 MCP 工具 |
| B站 cookie | `C:\deepseek\tools\bili-mcp\cookie.json` | 字幕/简介/评论受限，WBI 报 `code=-101` |
| bili-vision venv | `~\.dsh\bili-vision-venv\Scripts\python.exe`（faster-whisper 1.2.1 / ctranslate2 / av / numpy / yt-dlp） | 无字幕时无法 ASR |
| ffmpeg | `C:\deepseek\tools\bin\ffmpeg.exe` | 无法抽音频 |
| yt-dlp | bili-vision venv 内（2026.11.23）或 PATH | 无法下载视频 |
| Node | `C:\Users\ZQY\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe`（v24.21.0） | 脚本无法运行；不在 PATH 时用全路径 |

## 环境变量

| 变量 | 作用 |
|---|---|
| `BILI_MCP_DIR` | 覆盖 bili-mcp 目录（默认 `C:/deepseek/tools/bili-mcp`） |
| `BILI_VISION_PYTHON` | 覆盖 ASR 用的 python（默认 `~\.dsh\bili-vision-venv\Scripts\python.exe`） |
| `BILI_READER_DATA` | 覆盖数据目录（默认 `cwd\.bili-transcript`） |
| `BILIBILI_COOKIE_FILE` | `client.mjs` 调 MCP 时必须指到 `cookie.json` |
| `FORCE_ASR` | `1`＝跳过字幕直接 ASR（仍先读缓存） |
| `FORCE_CPU` | `1`＝强制 CPU；默认 `auto`，GPU 不可用自动回退 |

## 为什么不全搬

`transcript.mjs` 默认按绝对路径 `C:/deepseek/tools/bili-mcp` 找服务端（`BILI_MCP_DIR` 可覆盖）；复制到别的机器要改默认或设这个变量。bili-mcp 仍有独立登录态与 node_modules，不复制进技能，避免三份真相。
