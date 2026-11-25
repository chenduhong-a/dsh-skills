# ASR 失败与基线样本（实测）

> 这里只放数字与报错原文；判据在 `SKILL.md` 的「什么时候停」与「排障」。

## 1. 有声但无人声（2026-10-23，BV1bNns6BEEA）

- 时长 9:58；ffmpeg `volumedetect` 的 `mean_volume` 为 -13.5 dB，不是静音文件。
- faster-whisper base / CPU 对 0–30s、120s、300–340s 三段均为 0 段。
- 结论：纯 BGM + 屏幕演示，没有人声。脚本只打印 ctranslate2 的 `pkg_resources` warning，**真错误在 `tmp\<BV>.asr.err`**。

## 2. 短视频下载不全（2026-11-10，BV13W4J6kEHS）

- 时长 49 秒；两次运行都只返回 1 行空字幕（`source=ASR base`，`seconds` 为 14 / 10——**`seconds` 是耗时，不是视频时长**），缓存 txt 只有标题行。
- 删缓存 + `FORCE_ASR=1` 重跑，结果一样。
- 判据：拿 `bilibili_video_info` 的 `duration` 与缓存最后一条 `[mm:ss]` 对比；明显短＝yt-dlp 只下到一小段或音频为空。直接换 `bili_vision`，不在 ASR 上重试第三次。

## 3. 基线（2026-11-26，BV1v5n56QECK，6:42）

- 字幕通道 1.9 秒，`source=B站字幕`，216 行。
- `FORCE_ASR=1` 全链路 59.5 秒，`source=ASR base (forced)`，255 行；包含 360p 下载 + ffmpeg 抽音频 + base/CPU 转写。
- 说明 CPU 兜底可用；不要写成固定倍数，机器与视频不同会差很多。

## 4. MCP 工具数波动

- 2026-11-14 实测 22 个；2026-11-15 自检 31 个；2026-11-26 实测 22 个。
- 写代码前先 `client.mjs list`，不要照旧假设工具名；某些版本没有 `search`，报 `-32602 Tool not found`。
