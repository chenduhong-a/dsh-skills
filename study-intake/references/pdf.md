# PDF 线：先判有没有必要 OCR

## 一、决策树

```
doc_info 探底
├─ 有文字层 → doc_text 抽 1–2 页
│    ├─ 正文与公式都完整 → 直接用（零成本）
│    └─ 公式塌成乱码/空 → 走 OCR
└─ 无文字层（scannedPages 覆盖首页）
     ├─ 先查 _kb\kb.sqlite 有没有（doc_id + seq）
     │    └─ 有 → 直接复用，别重跑
     └─ 没有 → doc_ocr 试 3–5 页 → 确认质量 → prefetch 整本
```

**「有文字层」不等于「内容完整」**。PPT 转的 PDF、矢量排版的教材，文字层里往往只剩字壳子：公式变成一堆散字符、上下标混进正文、希腊字母变问号。所以一定要抽页看公式，不能只看「有没有字」。

## 二、探底与抽读

```
doc_info {path}                          # 页数、每页尺寸、文字密度、scannedPages、outline
doc_text {path, pages:"21-22"}   # 有文字层时抽读
doc_ocr {path, pages:"1-5", engine:"mineru"}   # 试 OCR
```

- `doc_info` 对 597 页的扫描书会把 300 个页号全列出来，一次约 1.5K token——只看结论就行，别逐条读。
- `doc_text` 对扫描页会回 `no text layer on pages="1" … use doc_ocr`，这是提示不是失败。
- 越界页会回 `no pages matched pages="999" (this PDF has 597 page(s))`。

## 三、跑 OCR

```
doc_ocr {path, pages:"1-3", engine:"mineru", force:true}
prefetch: doc_ocr {path, prefetch:true}          # 整本排队，立即返回
进度:      <cache>\ocr\progress.json
成图:      doc_ocr {path, withImages:true}
```

实测速度（RTX 5070 Ti Laptop，热态）：

| 类型 | 速度 | 备注 |
|---|---|---|
| 扫描书（37 MB / 597 页） | 2.37 s/页 | 约 24 分钟整本 |
| 矢量件（55.9 MB / 442 页） | 1.53 s/页 | 约 11 分钟 |
| 含表格（95.1 MB / 476 页） | 2.07 s/页 | 约 16 分钟 |
| 缓存命中 | 0.02 s/页 | 秒回 |

首次加载模型约 60 秒，常驻占 2.5 GB 内存 + 约 2.8 GB 显存。

**三个必踩的坑**：

1. **不传 `force: true` 会命中缓存**。用 `prefetch_book.mjs` 之类测速会得到 `0.0s` 的假象（它调工具时不传 force）。要测真实吞吐一律 `force:true`。
2. **`withImages` 默认 false**。此时 markdown 里仍写 `images/xxx.jpg`，但文件根本没下载——**悬空引用**。要图必须显式开，图落 `ocr\images\`，`img_file` 也才填绝对路径。prefetch 同样不取图。
3. **`probeLimit` 是「至少探这么多」不是上限**。已有 300 页记录时传 1 会复用旧结论，不是 bug。验证浅探测要用**没有缓存的新 PDF**。

缓存位置：

```
%USERPROFILE%\.dsh\storages\pdf-reader\<sha256 前16位>\
  ocr\pNNN.json      # 3 位补零，字段 schema/num/engine/text/markdown/blocks/withImages
  ocr\images\        # withImages 时才落
  pages\
  info.json          # 页数、元数据、scannedPages
  hash-index.json    # 路径 → {size, mtimeMs, hash}
```

**mtime 能区分引擎代次**：同一个 doc 里 p002–p005 是 10-24 用 3.1.6 跑的、p001 是 11-09 用 3.4.5 跑的，混着用没问题，但别拿旧页的结果推断新引擎质量。

## 四、体积限制

| 限制 | 数值 | 现象 |
|---|---|---|
| `doc_render` / `doc_info` 单文件 | 200 MB | `file too large (600366912 bytes > 209715200)` |
| StudyHub 单份材料 | 8 MB | 导入被拒 |
| 插件缓存总量 | 500 MB | `cacheAction: "prune"` 清 |

课件主版常超 200 MB——**验收换轻量版**（分辨率低但页序完全相同）。

## 五、入库

**`_kb` 入库走技能自带的 `scripts\kb_ingest.py`**（2026-11-17 起），不依赖已卸的知识库插件：

```powershell
# 0) 课程名不用先建：ingest 发现 courses 表没有它会自动插入（首次跑这门课）

# 1) 体检：要不要切、OCR 缓存齐不齐（不写库，只打印清单）
& $py $skill\scripts\kb_ingest.py split --pdf "<成品.pdf>" --out "<临时目录>"

# 2) 对上面列出的每份"未缓存"切分件调 doc_ocr（engine=mineru），跑完再回来

# 3) 灌库：默认 dry-run，看清抽样页再加 --go
& $py $skill\scripts\kb_ingest.py ingest --pdf "<成品.pdf>" --course 固体理论 `
    --rel "固体理论/固体理论_课件整理.pdf" --titles "固体理论\课件清单.json"
```

- 脚本自己判两条路：**有文字层**直抽（带清洗：`\r`、私用区公式字符、连续空行）；**无文字层**读 `doc_ocr` 的逐页缓存，缓存不全就报出还缺哪几份。
- `--titles` 给一个按页序的 `{title, group}` JSON（如该课的 `课件清单.json`），脚本用它写每页标题与 section；不给就写「第 N 页」。
- 三条硬坑（脚本已处理，别绕过重写）：①**体积上限按字节算**——`209715200` B 是 `doc_info` / `doc_render` 的硬闸，主版常超，**页数与抽页目视**用轻量版，顺序与字节、哈希仍用主版（轻量版重编码后字节必然不同）；②**OCR 缓存路径**——`%DSH_HOME%\storages\pdf-reader\<PDF 的 sha256 前 16 位>\ocr\pNNN.json`，先算 sha256 再定位目录；③**写完必须重建 FTS**——`items_fts` 是 external content 表、没有触发器，改完 `items` 要 `insert into items_fts(items_fts) values('rebuild')`，否则 `kb.cmd ask` 检不到新内容。
- 旧的 `_kb\app\add_book.py` 还在（`kb.py add` 转调它），但它写死的 `ocr-venv` 已随 pdf 插件卸载，没设 `KB_VENV` 会报 `FileNotFoundError`（2026-11-18 起插件自带那份 ocr-venv 也已删除）。

**导给 StudyHub 用 `scripts\kb_to_md.py`**（不要手写转换脚本）——它把 `kb.sqlite` 里的一份文档按章切成 md，每页带 `### PDF p.N` 锚点：

```powershell
# 先看这门课有哪些 doc（拿到 id 与 rel_path）
& $py $skill\scripts\kb_to_md.py --course 固体理论 --list

# 按章切成 md（默认 --group chapter；单份超过 --max-bytes 会自动再按页切）
& $py $skill\scripts\kb_to_md.py --doc-id 37 --out <临时目录>

# 然后逐份 study_workspace document.import（course 同名），再用 source.list 核对 total
```

- 为什么走 md 而不是原图 PDF：StudyHub 有两条上限——**PDF ≤ 200 页、文件 ≤ 8 MB**。648 MB 的扫描件两条都过不去，OCR 后的正文才进得去（原图仍留在 `_kb`，用 `kb.py page` 取）。
- md 导入每份只生成 **1 个 source**（PDF 是每页一个 source），所以 `sources` 计数只 +份数。


## 页标题清洗（扫描教材必做）

李正中 597 页验证过的四条，少一条章名就会乱：

1. **章名靠目录白名单**——把目录里的章名抄成 `BOOK_CHAPTERS` 常量，不要用「第X章 + 任意字」正则。OCR 会把正文残句吞进标题，正则一宽就全乱。
2. **双条件才算切换**：页首 50 字里同时出现「第X章」与某个章名片段，才认作新章首页；只有一个不动。
3. **章号只增不减**：正文会引用旧章（「见第三章」），若允许回退，后面整本书都会被带偏。
4. **跳过前 20 页**：封面、序、符号表、目录页里全是章名；先吃目录会让全书变成「第十二章」。

入库后抽 3–5 条核一遍：`kb.py find <章名> --course <课>`，看命中的 seq 是否落在那章应有的页码区间。
