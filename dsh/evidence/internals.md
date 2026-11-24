# DSH 内核取证：案例与实测证据

> 本文件是案例与实测证据，执行时不必读。执行口径（去哪找、怎么读、怎么判、红线）见 `references/internals.md`；这里只回答「那条判据是从哪次排查里来的」。按正文章节号组织，搬走的原文原样保留。

## 1. 服务注册与内核源码

**`webRuntime` 误判实例（rc.1 的版本行为细节）** —— 原文：

> 判据：`listService` 返回的是「精选契约目录」，不是全量注册表——**没列出来 ≠ 该服务不存在**。实例：rc.1 的 `webRuntime` 确实由 `@deepseek-ai/dsh-web-app` 提供（`lib/index.js:30` 常量、`:183 ctx.provide`），但目录里只有 `webhookRuntime` / `webServer`，据此曾误判服务缺失。

**asar 体积** —— 原文：

> 查内核源码：`app.asar` 是单文件 182 MB 明文，没有逐文件路径可直接翻。

## 2. 凭据、模型目录与能力声明

**401 且响应体为空的成因（字符数是当次实测）** —— 原文：

> 判据（401）：凭据要按名字取。`harness\.credentials.yaml` 里第一个 secret 是 `client-connection/browser-session`（43 字符），真正的 `DEEPSEEK_API_KEY` 是 35 字符、`sk-` 开头的值。按位置取第一条 → 两个接口双双 HTTP 401，且响应体为空，极易误判成 key 失效。

**同一坑的两副面孔** —— 原文：

> 同一个坑的两副面孔：一次是取错 secret 导致 401，一次是绕过本地 catalog 直连实测；两处都指向「按名字取钥、按 API 判能力」。

**`inputModalities` 判据的出处（行号属版本细节，升级后需重找）**：`dsh-llm-deepseek/lib/index.js:495-497` 的 `resolveRequestImagePolicy`。

## 3. 会话历史

**3.3「一条回答显示两遍」的渲染层判定样本** —— 原文：

> 实例：那次 reasoning 1,665 字 + text 550 字，没有第二份 text，判定为渲染层。

**3.3 括号里的实验性归因（当时未定论，只作线索）** —— 原文：

> 渲染层重复（流式预览残留 + 最终消息叠加，可能与 `cot-translation` 实验 bundle 有关）

**3.4 丢坏帧修法的实测帧数** —— 原文：

> 实测 1988 帧删 1 帧 → 1987 帧 / 4439 行 / seq 无 gap。

## 4. GUI 现场

**三类 console 噪音的完整原文（含 9230 端口与命令）** —— 原文表行照录：

> | `WebSocket connection to 'ws://127.0.0.1:9230/ingest' failed`（红屏刷） | 内核 experimental-inspector worker 的时序噪音 | `Get-NetTCPConnection -LocalPort 9230 -State Listen` 有监听即已恢复，清空 console |
> | `LaTeX-incompatible input … Unicode text character "（" used in math mode`（黄） | `$...$` 里混进中文标点（`（` `）` `，`）；KaTeX 只 warn 不炸 | 把中文标点留在公式外 |
> | `[dsh-raw-html-v2] 渲染边界捕获`（红 + stack） | 真渲染异常（React 错误边界），只降级当前消息 | 在 console 过滤「渲染边界」，否则被前两类淹没 |

**`VcpErrorBoundary` 的实现（版本行为细节）** —— 原文：

> 相关：`dsh-raw-html-v2` 的 `VcpErrorBoundary` 用 `componentDidCatch`，只降级当前消息并打这条日志，不扩散到整页。

## 5. 上下文账与请求体

**5.1 那次超限报错原文**：

```
maximum context length is 1048576 tokens. However, you requested 1503615 tokens (1247615 in the messages, 256000 in the completion)
```

**5.1 当时的对账结果** —— 原文：

> **先别认错**——用 `acp_status` 看 BILLED INPUT 确认是不是当前会话（那次当前会话只 144K，报错来自别处长会话）。

**5.1 输出预留的来历** —— 原文：

> 输出预留 256K 是给 deepseek-flash 的 `max_tokens`，1M 扣掉它只剩 768K 给上下文。

**5.2 400 的排查过程（改上下文大小、改 preset 名均无效，才回到工具投影）** —— 原文：

> **症状**：会话中途换过工具面（PTC ↔ 标准、装卸插件）后，上游返回 400（与 `defer_loading` 有关）；改上下文大小、改 preset 名都无效。
