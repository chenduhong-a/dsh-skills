---
name: doc-parsing
author: "ZQY-LD"
description: PDF、扫描件与 docx/pptx/xlsx 取文本、公式、表格、图片的选路手册——先分诊（PDF 看有没有文字层、是不是扫描件、公式在哪一层；Office 看是读表取文、抽公式还是转 PDF），再进对应篇：PDF 篇讲通道与验真、页序与结构坑，Office 篇讲 OOXML 直读、COM 转 PDF 与私用区编码。当任务涉及「解析 PDF / 扫描件 OCR / 提取课件公式 / 读 PDF 表格 / 页码对不上 / 读 xlsx / 读 docx / Office 转 PDF / 满屏方框 / 本地 MinerU 服务排错」时加载。**不用于**：生成或编辑 Office 文档（见 `univer` 系列）、批量整理课件成册（见 `study-intake`）、网页抓取（见 `browser-skill`）、纯图片理解（见 `bili-vision` 或直接读图）。
---

# 文档解析手册

先分诊，再选篇。**两篇互不依赖**——只读你要的那一篇，别通读。带日期的实测数字在 `evidence/` 两篇里，环境与端口在 `DEPENDENCIES.md`，正文只留判据。**数据截止 2026-11-26**：MinerU 4.2.3、`dsh-doc-parser` 0.3.15；下文数字只作量级参考，档位与开关以本机文件为准。

## 判据：先给文件分诊

| 来料 | 去哪读 | 一句话 |
|---|---|---|
| PDF 有文字层 | `references/pdf.md` §1 | `doc_text` 直接取，别先 OCR |
| PDF 是扫描件（`/Font` 为 0） | `references/pdf.md` §1.6 | 整篇 Markdown 走 `doc_parse`；决定不上传就 `doc_ocr` 逐页再拼 |
| 结果可疑（怕吃了缓存、没真跑） | `references/pdf.md` §2 | 认 `batchId` / `submittedAt`，或比内容，别信页头 `(ocr …)` |
| 页码对不上 | `references/pdf.md` §3.5 | 三套口径：物理页 / 印刷页 / 课件标号，先对齐再交付 |
| 公式只在图里、或藏在 OLE 里 | PDF → `references/pdf.md` §4；PPT → `references/office.md` §3 | 先弄清公式存在哪一层，再选路 |
| xlsx / docx 取文本与表格 | `references/office.md` §1 §2 | 先试 openpyxl / python-docx，别上手写正则 |
| Office 转 PDF | `references/office.md` §4 | 批量走 LibreOffice，单件要保真走 COM |
| 打开是满屏 `□` | `references/office.md` §5 | 私用区字符，不是字体缺失 |
| 本地 CLI 一页十几秒、要直调 API | `references/pdf.md` §1.2 | 4.x 是 `18000`（异步）`+ 18001`（同步单文件）两个进程 |
| 本地太慢或服务不通，要换在线 | `references/pdf.md` §1.3 | 隐私开关在 `mineru-mode.txt`；先跑探针脚本 |
| 装 OCR 引擎报错、`import onnxruntime` 崩 | `references/pdf.md` §1.4 | OCR 只剩 MinerU；`0xC0000005` 先修 VC 运行时，别钉旧版 |
| 要四档谁快谁准、某页为什么走了 advanced | `evidence/mineru-measurements.md` | 数字与口径都在这里 |

## 选篇

| 篇 | 装什么 | 什么时候读 |
|---|---|---|
| `references/pdf.md` | 通道选择、四档与自动分档、验真、PDF 结构、公式与图、页码基准 | 任何 PDF / 扫描件任务 |
| `references/office.md` | xlsx / docx 读法、PPT 公式三条路、COM 与 LibreOffice 转 PDF、PUA | 任何 docx / pptx / xlsx 与旧 `.doc` / `.ppt` 任务 |
| `evidence/` | `mineru.md` 版本与逐版修复史；`mineru-measurements.md` 实测数字 | 查「当时为什么这么改」「谁更快」时才读 |

## 跨篇铁律

1. **先验真再交付**：页头 `(ocr …)` 只是引擎名，不区分缓存与真跑。**`doc_parse` 认结果包的 `batchId` / `submittedAt`（只有它返回这两个字段）；`doc_ocr` / `doc_tables` 不返回字段，只能比内容——抽一页看文本是不是变了**，或退一步看输出文件 mtime（最弱）。
2. **页码先说口径**：物理页 / 印刷页 / 课件标号三套，交付里写「PDF 第 N 页（＝印刷 pM）」。
3. **图要落盘校验**：Markdown 里出现过 `![](…)` 不代表文件存在。
4. **不确定就停**：来源文件拿不到、页码对不上、公式层不明——先问，别猜着跑完再返工。

## 脚本

| 脚本 | 用途 | 怎么跑 |
|---|---|---|
| `scripts/mineru-online-probe.mjs` | 探在线 MinerU 是否可用、token 是否有效（不拿真教材试）。**什么时候跑**：在线 token 疑似失效、换网络 / 换机器、或想先确认通不通会不会白传文件时 | `& $NODE_BIN <本技能目录>\scripts\mineru-online-probe.mjs` |

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
| `MINERU_VENV` | MinerU 4.2.3 的 venv | `C:\deepseek\tools\mineru4-venv\Scripts\python.exe` | 自建，固定后写回本表（4.2.3 升上来之后旧 3.x venv 已删，只剩这一条本地通道） |

换机器三步：①确认 `DSH_HOME`、`SKILLS_DIR`、`NODE_BIN`；②本技能只有一个脚本 `scripts/mineru-online-probe.mjs`，常量在文件顶部（API 地址、token 路径），改成新路径再跑；③其余判据（版本号、报错串、行号、端口规则）与具体路径无关，通常不用改。
