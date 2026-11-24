# 依赖清单（bili-transcript）

## 脚本
- 外部主脚本：`C:\deepseek\tools\bili-reader\transcript.mjs`（214 行）
- 技能内副本：`scripts/transcript.mjs` —— 同一份代码，**唯一差别**是把 `path.join(here,'..','bili-mcp')` 改成 `process.env.BILI_MCP_DIR || 'C:/deepseek/tools/bili-mcp'`
- ASR 脚本：`scripts/asr.py` —— faster-whisper 转写（2026-11-24 从 `dsh-video-understand` 迁入；解码成 numpy 再喂模型，绕开 `av.open(metadata_errors=...)` 兼容错误）
- 未复制的兄弟脚本：`batch.mjs`（批量 MCP 调用）、`opus-read.mjs`、`opus-probe.mjs`，仍在 `C:\deepseek\tools\bili-reader\`

## 外部依赖
| 依赖 | 路径 | 缺了会怎样 |
|---|---|---|
| bili-mcp 服务端 | `C:\deepseek\tools\bili-mcp\node_modules\bilibili-mcp-server\dist\index.js` | 字幕通道不可用，只能 yt-dlp + ASR |
| B站 cookie | `C:\deepseek\tools\bili-mcp\cookie.json` | 字幕/简介/评论受限 |
| bili-vision venv | `~\.dsh\bili-vision-venv\Scripts\python.exe`（faster-whisper 1.2.1 / ctranslate2 / av / numpy / yt-dlp） | 无字幕时无法 ASR（2026-11-24 起由它承担，原 video-understand venv 随插件卸载已消失） |
| ffmpeg | `C:\deepseek\tools\bin\ffmpeg.exe` | 无法抽音频 |
| yt-dlp | bili-vision venv 内（2026.11.23 装的）或 PATH | 无法下载视频 |

## 为什么不全搬
`transcript.mjs` 靠 `here/../bili-mcp` 找兄弟目录，原样复制到技能目录必然找不到；副本已把该路径改成绝对路径 + 环境变量覆盖。其余脚本仍留原处，避免三份真相。
