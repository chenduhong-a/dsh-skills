# 入库：把成品 PDF 送进 `_kb\kb.sqlite`

> **知识库插件 `@local/dsh-knowledge-base` 已于 2026-11-16 卸载**：它提供的 `kb_*` 工具全部不可用，文中引用一律按「已卸」读。下面走的是技能自带的 `scripts\kb_ingest.py`（入库）与 `scripts\kb_to_md.py`（转 md），直接读写 `_kb\kb.sqlite`，**不依赖插件**。
>
> **查询命令不在这里**——用 `_kb\kb.cmd`（硬编码 `%~dp0app\kb.py`，优先 `%~dp0py\Scripts\python.exe`、回退 runtime python），细节见 `kb-ops` 技能。

## 三个目标，三条手段

| 目标 | 手段 | 判据 |
|---|---|---|
| 知识库 `_kb`（**主线**） | `scripts\kb_ingest.py`，三步：`split` 体检 → `doc_ocr` → `ingest` | `kb.cmd find <词> --course <课>` 能命中；`kb.cmd page <doc> <seq>` 能取原页 |
| StudyHub 材料（可选） | `scripts\kb_to_md.py` 生成 md → `document.import` | `source.list {course, groupBy:"document"}` 的 total 等于生成份数 |
| StudyHub 题目（可选） | 已有题用 `document.import` / `deck.import` | decks / cards 计数变化 |

**两个可选目标是可选的**：不装 StudyHub 时只做第一行。自学线（`study-flow`）不依赖 StudyHub，也不读它的数据——两条线各走各的。

## StudyHub 的三档上限（别再只写「200 页 8 MB」）

权威契约在 `library.context {area:"imports"}`，原文两条：

- **体积**：pdf / md / tex / html / txt **≤ 8 MB**；docx / pptx / ppt / JSON **≤ 40 MB**；
- **页数**：PDF **≤ 200 页**，超了**无论 `pages` 怎么写都拒**（`pages` 只能在一个达标文件里再收窄范围）；
- **文本量**：单次导入抽取的文本 **≤ 600000 字符**（页数少或拆开就不超）；
- 文本类文档必须是 **UTF-8**。

所以「一份 300 页的 PDF 用 `pages` 只取前 50 页」**不行**——页数闸在 `pages` 之前。

## 为什么走 md 而不是直接传 PDF

上面两条闸决定了：扫描课件动辄几百页、几百 MB，原 PDF 过不去；而 OCR 后的正文按页存在 `kb.sqlite` 里，按章切成几份 md 就能全部进库，且每页自带锚点，要回原页图时用 `kb.cmd page`。

## `kb_ingest.py` 的三个子命令

```powershell
# 1) 体检：要不要切片（体积与页数两个判据都看）
& $py $skill\scripts\kb_ingest.py split --pdf <成品.pdf> --out <临时目录>

# 2) OCR（有文字层就跳过这步）
#    先用 doc_ocr 试 3–5 页，再整本 prefetch

# 3) 灌库（默认 dry-run，确认后加 --go）
& $py $skill\scripts\kb_ingest.py ingest --pdf <成品.pdf> --course <课程> `
    --rel '<课程>/<成品.pdf>' --titles <课件清单.json> [--go]
```

几个要点：

- **`--titles` 强烈建议给**：不给时 `items.title` 取正文首行，给 `课件清单.json` 就用精修标题。页标题是入库质量的一半。
- **必须按 `split` 的规则切**（`CHUNK_PAGES = 100`，产出 `part_{start+1}-{end}.pdf`）。自己另造 200 页的片哈希不同、OCR 缓存不命中，白跑一轮。
- **OCR 会有页失败**（手写黑板最常见，返回 `page missing in online result`）。`ingest` 会把这些页打成「正文留空但保留页序」的条目，标题照常对齐——看到这条提示不用修，只需知道那几页查不到正文。
- **写完必须重建 FTS**：`insert into items_fts(items_fts) values('rebuild')`。`items_fts` 是 external content 表、没有触发器，不 rebuild 就检索不到（详见 `kb-ops` 的 `references/schema.md`）。
- **`page` 的第二个参数是 PDF 页序，不是书页码**——`pagemap` 有 offset 但 `cmd_page` 不读它，传书页码会静默渲染错页。

## OCR 缓存在哪

`%DSH_HOME%\storages\pdf-reader\<PDF 内容 sha256 前 16 位>\ocr\p{i:03d}.json`。

**缓存按 PDF 内容哈希分目录**，所以：换了文件（哪怕只重渲染一次）就是新目录，全要重 OCR；反过来，同一份文件重跑一定命中。判断命中用 `doc_ocr` 的 `cacheAction: "stats"`。

## 知识库目录分层（2026-11-19 定）

`_kb\` 按用途分组，根目录只留入口与数据——二十七项混放时用户原话「这个看着好乱」：

```
_kb\
├─ kb.cmd  kb.sqlite  README.md  _cache\   ← 入口、库、页面缓存
├─ app\       8 个脚本（kb.py / add_book / download_model / embed / export_md / index_vec / kb_textlayer / reocr_indra）
├─ docs\      勘误三件 + README_插件缓存.md + formulas\ 公式表
├─ models\    bge 系列 —— 运行依赖，不是缓存
├─ backup\    旧库 + code_before_move\ 代码原件
└─ digest\    5 门课的摘要素材（KaTeX 等前端资源在 pdf 插件里，_kb 下没有 vendor\）
```

搬动后要跟着改的三处：①脚本里取同目录资源用 `APP = os.path.dirname(os.path.abspath(__file__))`，不要拿 `KB` 拼脚本名；②`embed.py` 的 `MODEL_DIR` 与 `index_vec.py` 的 `DB` 上跳一级（`dirname(dirname(__file__))`）；③`kb.cmd` 指向 `app\kb.py`，不要指向根。改完把 `kb.cmd status`、`kb.cmd find`、`kb.cmd page`、`index_vec.py`、`kb.cmd check` 各跑一遍再算完成。

> **缺 `models\` 时不是全瘫**：入库本身不依赖向量模型；`find` 只降级（剩 FTS/LIKE），`ask` 完全不受影响（它是纯文本实现）。完整依赖表见 `DEPENDENCIES.md`。

## 库路径不是默认值时

`scripts\kb_ingest.py` 与 `kb_to_md.py` 的默认库路径是作者机器上的 `C:\deepseek\study\_kb\kb.sqlite`。换机器先：

```powershell
$env:STUDY_KB_DB = '<你的 kb.sqlite 路径>'
```

否则报 `unable to open database file`。
