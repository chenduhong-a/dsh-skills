# 依赖清单（study-intake）

## 技能自带脚本

- `scripts\kb_ingest.py` —— 三步：`split` 体检 → `doc_ocr` → `ingest`
- `scripts\kb_to_md.py` —— 把 `_kb` 里的条目转成 md（送 StudyHub 用），**不依赖已卸的 `@local/dsh-knowledge-base`**（那插件 2026-11-16 已卸，它的 `kb_*` 工具全部不可用）
- **查询命令不在本技能里**：用下面的「查询入口」`_kb\kb.cmd`（2026-11-26 前的版本在这里误列过一个不存在的查询脚本，已删）

## 外部依赖

| 依赖 | 路径 | 缺了会怎样 |
|---|---|---|
| 知识库根 `_kb` | 本机 `C:\deepseek\study\_kb` | 入不了库 |
| 查询入口 | `_kb\kb.cmd`（硬编码 `%~dp0app\kb.py`，优先 `py\Scripts\python.exe`、回退 runtime python） | 只能直接用 SQL 查，本机没有 `config.json` |
| 向量模型 | `_kb\models\bge-small-zh` | `kb.py ask` 直接瘫；**这是运行依赖不是缓存，别当垃圾清** |
| OCR 引擎 | `doc_ocr` 工具（`dsh-doc-parser` 插件）+ MinerU 通道 | 扫描件提不出文字，只能进文字层 PDF |
| 旧 ocr-venv | 已随 pdf 插件删除（`_kb\app\add_book.py` 里的 `ocr-venv` 不存在） | 没设 `KB_VENV` 会 `FileNotFoundError` |
| StudyHub | 可选插件 | 不影响入库，只少「送进学习库」这一段 |

## 缺 models 的降级

**入库本身不依赖向量模型**：`kb.py find` / `page` 可用、`kb.py ask` 不可用。所以「模型没了」不等于「这批材料白入库」，先核 `items` 行数再说。

## 已知上限

StudyHub 两条硬上限：**PDF ≤ 200 页、文件 ≤ 8 MB**——扫描件过大所以走「OCR 后只送正文 md、原图留在 `_kb`」这条路。
