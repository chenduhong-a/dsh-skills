# 依赖清单（doc-parsing）

> 数据截止 **2026-11-26**。路径符号含义见 `SKILL.md` 附录「路径约定」；实测数字见 `evidence/mineru-measurements.md`。本文件只写「缺了什么会坏、怎么查」。

## 一、必需：`dsh-doc-parser` 插件

| 项 | 值 | 缺了会怎样 |
|---|---|---|
| 插件 | `dsh-doc-parser` **0.3.15**（profile 里 `link:` 到 `$TOOLS_DIR\dsh-doc-parser`） | `doc_*` 工具整片 unknown，本技能所有通道失效 |
| 插件常量目录 | `$TOOLS_DIR\dsh-doc-parser\` | 开关文件与 token 都按这个目录找 |
| Node | `$NODE_BIN`（DSH 自带运行时，v24） | 在线探针脚本跑不起来 |

**判据（分三样）**：

- 工具在不在 → 任一 `doc_info` 能返回结果；
- 插件启用没有 → 工具整片 unknown 先查 `dsh.profile.bundles`（**装了 ≠ 启用**），再看 profile 的 `package.json` 有没有 `dsh-doc-parser`；
- 走哪条通道 → `doc_ocr` 页缓存 `p%03d.json` 的 `via` 字段（`online` = 在线，空 = 本地），**不是页头 `(ocr mineru)`**（细则见 `references/pdf.md` §2.2）。

**版本刷新命令**（升级过插件或 MinerU 之后先跑这个，本文件与 `evidence/mineru.md` 的数字才算数）：

```powershell
(Get-Content "$PROFILE_DIR\package.json" -Raw | ConvertFrom-Json).dependencies.'dsh-doc-parser'
& "$TOOLS_DIR\mineru4-venv\Scripts\mineru.exe" --version
```

## 二、配置开关（两个文件 + 一个约定）

| 文件 | 值 | 作用 | 判据 |
|---|---|---|---|
| `$TOOLS_DIR\dsh-doc-parser\mineru-mode.txt` | 一行 `local` 或 `online` | 本地 / 在线通道；隐私开关 | 值不认识（含空文件）**直接报错**，不回落环境变量（0.3.12 起 fail-closed）；只对**扫描件与图片型 PDF**生效，有文本层的走 PDFium |
| `$TOOLS_DIR\dsh-doc-parser\mineru-tier.txt` | 一行 `flash` / `basic` / `standard` / `advanced` | 档位；本机现为 **`standard`** | 每次调用重读，改完不必重启宿主 |
| `$TOOLS_DIR\.mineru-token` | 一行 token | 在线通道凭据，有效期 90 天、额度 5000 文件/天 | 拿不到/过期 → 在线 403；**先跑 `scripts/mineru-online-probe.mjs` 再拿真文件试** |
| `MINERU_MODE` / `MINERU_TIER` | 环境变量 | 没有开关文件时才看 | Windows 改用户级环境变量不刷新已运行的 explorer，**改完不一定生效**，别拿它当主开关 |

`MINERU_HTTP_MAX_MB` 默认 **200 MiB** 是**内存**闸门（整本必须读进内存），与这次解析几页无关——整本超了就是超了，`pages` 收窄也救不回来（`references/pdf.md` §1.2）。

## 三、本地 MinerU：venv + 两个进程 + 两个端口

| 项 | 值 | 说明 |
|---|---|---|
| venv | `$TOOLS_DIR\mineru4-venv\Scripts\`（`mineru.exe` / `python.exe`） | 4.2.3；旧 3.x venv 已删，只剩这一条本地通道 |
| 异步 API | `mineru-api.exe`，端口 **18000** | 只有 `/v1/tasks` 异步口 |
| 同步单文件 | `mineru-kit file-parse-server --api-url http://127.0.0.1:18000 --port 18001` | 对外 `POST /v1/file_parse`；**只起 18000 不够** |
| 模型目录 | `%USERPROFILE%\.mineru` | basic = ONNX 小模型（`MinerU-4_models_onnx`）；standard 另加 `MinerU2.5-Pro-2605-1.2B` GGUF（531 MB + 709 MB mmproj） |
| 模型查看 | `& $TOOLS_DIR\mineru4-venv\Scripts\mineru-kit.exe models show` | 看 `就绪` 与缺失项 |

**判据**：`doc_ocr` 报「18000 / 18001 没在跑」时，先看这两个端口有没有监听，再看 venv 里有没有 `mineru-kit.exe`（有它时插件会拦住 3.x 的 CLI 兜底，见 `references/pdf.md` §1.2）。

**四个排错方向**（还没写成完整排错段，按此顺序查）：`MINERU_API_URL` 指对没、模型是否缺失（`models show`）、显存是否够（整本 510 页课件 standard 常驻约 2 GB 级）、端口是否被占。服务不通时按 `references/pdf.md` §1.2 退回 CLI 或转在线。

## 四、可选：Office 与转 PDF

| 项 | 用途 | 缺了会怎样 |
|---|---|---|
| Microsoft Office / WPS（COM） | 旧 `.doc` / `.ppt` 打开、单件保真转 PDF | 改走 LibreOffice；WPS 的 ProgID 是 `KWPP.Application` / `Kwps.Application` |
| LibreOffice（`soffice.exe`） | 批量转 PDF、pptx 公式 OCR 前置 | 公式提取走不通，只能 `doc_render` 出图再视觉读 |
| Python `openpyxl` / `python-docx` | 读 xlsx / docx | 只能解包直读 XML（`references/office.md` §1.3、§2.1） |

三者在同一台机器上可并存；`.doc` / `.ppt` 一律「转 PDF 再抽文字层」最省事（`references/office.md` §2.2、§4）。
