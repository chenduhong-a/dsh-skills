---
author: "ZQY-LB"
name: study-intake
description: "把一门课散落的课件整理成一份能翻能查的成品 PDF，并送进知识库（可选送 StudyHub）——手机翻拍的投影幕照片、原始 .ppt/.pptx、扫描版或矢量 PDF 三类来料各有流程。当用户说「我又放了一批课件」「这批照片帮我整理」「把课件入库」「这个 PDF 怎么进库」时使用。不用于出题、出学习总结与复习资料（见 study-flow）、只解析某一页取文本（见 doc-parsing）、编辑 Word/Excel/PPT 成品（见 univer 系列）。"
---

# 课件入库（study-intake）

> 版本号见 `CHANGELOG.md` 顶部。frontmatter 里不写 `version`——技能加载器不读它。

把「一堆原始文件」变成「一份带书签的成品 PDF + 可检索的正文」，中间每一步都能被目视或哈希验证。
**出题、出学习类 PDF 不归这里**——那是 `study-flow` 的事，本技能到「入库」为止。

## 运行前：把两个符号设成你的

下面所有命令块里的 `$py` 与 `$skill` 是本机路径，**照抄前先在当前 PowerShell 里设一次**：

```powershell
$py    = '<你的 python 可执行文件>'   # 要能 import cv2 / pypdf / pypdfium2 的那只，见 references/scripts.md 的依赖自检
$skill = '<你的 skills 根>\study-intake'
```

其余占位符按当次实际填：`<课程>` = 这门课的资料目录名。两个变量没设就照抄，报的是「找不到文件」或 `ModuleNotFoundError`——那不是脚本坏了。
库路径不是 `C:\deepseek\study\_kb\kb.sqlite` 时先设 `$env:STUDY_KB_DB`，否则 `unable to open database file`（见 `references/ingest.md`）。

## 0. 先判来料，选入口

| 来料 | 典型形态 | 走哪条线 |
|---|---|---|
| 手机翻拍投影幕 | `IMG_YYYYMMDD_HHMMSS.jpg` 几百张，尺寸 4320×5760 | **照片线**（§1） |
| 原始 PPT | `.ppt` / `.pptx`，一讲一个文件 | **PPT 线**（§2） |
| 扫描书 / 矢量教材 / 别人给的 PDF | `.pdf` | **PDF 线**（§3） |

**注意「扫描书」与「矢量教材」虽然都是 PDF，处理完全不同**：前者要 OCR 几百页，后者抽文字层直接用。判据在 §3 的决策树，不在「来料类型」这一栏。

三条线最后都汇到**入库**（§4）与**验收**（§5）。

## 1. 照片线：翻拍照片 → 三件套 PDF

**六步，每步都有验收动作，跳步会在最后一次性爆出来。**

### 1.1 归置批次

文件名里有时间（`IMG_20261104_080136.jpg` = 11-04 08:01:36），**按这个分批次、排顺序，不看文件修改时间**。先读首末两张判断内容接续：接上一批就并进同一本，开新章就新起一段。

```
<课程>\照片原件N\         ← 原始照片，零修改
<课程>\照片裁切件N\       ← 裁切产物，文件名与原件同名
<课程>\课件清单.json       ← 主版清单（指向裁切件）
<课程>\课件清单_未裁剪.json  ← 未裁剪版清单（指向原件）
```

### 1.2 裁切

```powershell
& $py $skill\scripts\crop_portrait.py 照片原件5 照片裁切件5
```

**先看报告里的 `areaPct`**：低于 15% 的可能是深色底幻灯片（灰度判据把整片背景当成内容），用 `fix_blue.py` 重裁并看预览红框：

```powershell
& $py $skill\scripts\fix_blue.py 照片原件5 照片裁切件5 IMG_20261104_104519.jpg IMG_20261104_111007.jpg
```

宽高比 `<1.0` 或 `>2.0` 会单独列「可疑」（竖拍裁完应在 1.0–2.0）。**面积与宽高比是两张独立的表，不是「且」的关系。** 算法与判据见 `references/photos.md`。

### 1.3 目视验收：缩略图墙

```powershell
& $py $skill\scripts\make_sheet.py 照片裁切件5 _tools\sheet 5
```

生成 5×4 的墙，**逐墙 `read_image` 看**：内容是否完整、有没有裁掉半行、有没有把观众人头当屏幕。**这一步不能省**——算法指标只能排序可疑度，不能替代眼睛。

**页码看图上打的号，不要数格子**：40 张以上数格子必错（裁切后长宽比不一，网格会错位）。标签由 `make_sheet.py` 用 **PIL 的 `ImageDraw.text`** 印在每格下方，**不经过 cv2**——标签没出来别去查 cv2。

### 1.4 定分段

看完墙才知道这一批跨了哪几节。写成分段表 `时间段 → 分组名`，颗粒度对齐「章 › 节」：

```json
[["080136", "第四章 晶体缺陷 › 点缺陷与缺陷团簇（11-04 续）"],
 ["080354", "第四章 晶体缺陷 › 线缺陷：位错"]]
```

新批次**标题一律先写「第 N 页」占位**，精修另做；测边界时先给 2–3 个候选起点各跑一遍 `--dry-run`，别只试一个。

### 1.5 追加清单

```powershell
& $py $skill\scripts\append_batch.py --manifest 课件清单.json --raw-manifest 课件清单_未裁剪.json `
    --crop-dir 照片裁切件5 --src-dir 照片原件5 --seg seg.json [--dry-run]
```

它会：先备份 `.bak_<时间戳>` → 校验两目录张数一致 → 追加 → 只在**本批范围**内把「第 0 页」改成真实页号（老条目的真标题绝不覆盖）→ 打印本批分组分布。

### 1.6 重建三件套

```powershell
& $py $skill\scripts\build_all.py --dir . --name <课程> --cropped 课件清单.json --raw 课件清单_未裁剪.json
```

产出主版 / 轻量版（长边 2000、q82）/ 未裁剪版，**页数必须三者相同**。

## 2. PPT 线：原始 PPT → 合并册

### 2.1 转 PDF

`.ppt`（旧二进制）先转 PDF 再谈入库。两条路：

- **LibreOffice**（公式密集或后面要 OCR 时更省事）：`& 'C:\Program Files\LibreOffice\program\soffice.exe' --headless --convert-to pdf`。**裸 `soffice` 不在 PATH**；不加 `--headless` 会弹 GUI。本机 26.8.2.2，实测 54 页 3.9 秒。
- **WPS COM**：**一个文件一个实例**，同一实例转第二个必崩 `0x800706BA`。完整代码见 `references/pptx.md`。

### 2.2 合并加书签

```powershell
& $py $skill\scripts\merge_pdfs.py --out <课程>_课件整理.pdf --dir _pdf `
    --pattern '^高量(\d+)-(.+)\.pdf$' --label '第{n}讲  {t}' --title '<课程> 课件整理'
```

输出末尾必须报「页数合计 / 体积 / 每讲起始页」，与各文件页数相加对得上。

### 2.3 公式（只有 PPT 里有 MathType 公式时才做）

MathType 公式是 **OLE 嵌入对象**，不是 Office 公式：`ppt/embeddings/oleObject*.bin` 内含 `Equation Native` 流，现成插件只读 `a:t` 正文层，**拿不到公式**。

`doc_formulas action=scan` 先数（oleObject 数 + WMF/EMF 分布）→ `doc_formulas action=extract` 出 LaTeX（内部走 LibreOffice 转 PDF → 逐页 OCR，只取公式块，带页码）。实测 67 个公式 / 32 页 / 40.8 秒。

- **WMF/EMF 抽图路线已弃用**：字体渲染型，`System.Drawing` 不认 MT Extra/Symbol，10 个课件里 9 个出乱码。
- **别解 MTEF**：无公开规范，开源库只到 v5，约 10 轮未通、字符码错位。

细节与校验见 `references/pptx.md`。

## 3. PDF 线：判有没有必要 OCR

```
doc_info 探底（页数 / 文字层 / scannedPages / 体积）
  ├─ 有文字层 → doc_text 抽 1–2 页，看公式有没有塌
  │     ├─ 干净   → 直接用
  │     └─ 塌了   → 走 OCR
  └─ 无文字层 → 先查 _kb\kb.sqlite 里是否已有（doc_id + seq），有就复用
                → 没有才 OCR：先 doc_ocr 试 3–5 页，再整本 prefetch
```

OCR 前先看缓存命中（`cacheAction: "stats"`）；跑整本用 `prefetch`，进度落 `ocr\progress.json`，不要轮询单页。

**三个上限都要看**：

1. 单份 **≤ 200 MB**（`209715200` B，插件 `main.js:35` 的 `MAX_BYTES`——它管**所有 `doc_*`**，`prepare()` 有 7 个调用点，不止 `doc_ocr`；超了报 `file too large (>209715200)`）；
2. **≤ 200 页**（MinerU 在线硬限，超了报 `number of pages exceeds limit (200 pages)`）；
3. 走在线 MinerU 时 **≤ 120 MB**（`MINERU_HTTP_MAX_MB` 默认值，超了整本掉 CLI 兜底）。

> **190 MB 不是工具闸**：`kb_ingest.py:42` 的 `LIMIT_BYTES = 190 * 1024 * 1024` 是本技能自己留的 10 MB 余量，别把它当成工具的判定线。

**体积达标不代表能跑**——510 页 116 MB 的轻量版就是被页数拦下的。超了就 `split` 体检，它按 `CHUNK_PAGES = 100` 切；**必须按它的规则切**，自己另造片哈希不同、OCR 缓存不命中。

OCR 会有页失败（手写黑板最常见，返回 `page missing in online result`）。`ingest` 会把它打成「正文留空但保留页序」的条目，标题照常对齐——看到这条提示不用修，只需知道那几页查不到正文。

**页标题是入库质量的一半**：扫描教材的页标题清洗有四个坑（目录白名单、页首双条件、章号只增不减、跳过前 20 页），做法见 `references/pdf.md` 末节「页标题清洗」。

## 4. 入库

三步：`split` 体检 → `doc_ocr` → `ingest`（**默认 dry-run，确认后加 `--go`**）。

```powershell
& $py $skill\scripts\kb_ingest.py ingest --pdf <成品.pdf> --course <课程> `
    --rel '<课程>/<成品.pdf>' --titles <课件清单.json> [--go]
```

`--titles` 强烈建议给——不给时 `items.title` 取正文首行，给 `课件清单.json` 就用精修标题。写完必须 `insert into items_fts(items_fts) values('rebuild')`，否则检索不到。

**查询用 `_kb\kb.cmd`，不在本技能里。** 完整命令、缓存在哪、库目录分层、StudyHub 的三档上限（**8 MB / 40 MB / 200 页 / 60 万字符**）都在 `references/ingest.md`。

## 5. 验收（五条不过就不交付）

细则与命令在 `references/verify.md`，两处口径一致。

1. **页数**：`doc_info` 的 pages 与清单条数相等；三件套三者相等。
2. **顺序与字节**：`scripts\verify_order.py` 抽 PDF 内嵌图像逐页与清单图片比 SHA256，必须 `order + bytes identical: PASS`——一条同时排除顺序错、图被换、编码失真。
3. **书签**：`doc_info` 的 outline 顶层分组数与分段表一致（多批次成书时只核「本批分组都在」）。
4. **抽页目视**：首批一页、中段一页、末页一页，`doc_render` 渲染后 `read_image`——内容必须对得上批次边界。
5. **哈希**：桌面副本与工作区成品 SHA256 一致（`Get-FileHash`）；先 `Copy-Item` 过去再比。

**主版常超 200 MB**，`doc_render` / `doc_info` 会报 `file too large (>209715200)`——**页数与抽页目视**用轻量版（只差分辨率，页序完全相同）；但**顺序与字节、哈希必须用主版**。轻量版把 JPEG 重编码成 2000/q82，字节必然不同，拿它跑 `verify_order.py` 只会得到 `MISMATCH`（实测主版 PASS、同一清单轻量版 FAIL 3 处）。

## 6. 八条不变量

1. **原件不动**：`照片原件N` 只读，所有裁剪写到 `照片裁切件N`。
2. **先备份再改清单**：任何清单写入前 `.bak_<时间戳>`。
3. **只在新增范围内改标题**：老条目的真标题绝不被「第 N 页」覆盖。
4. **算法只排可疑度，验收靠眼睛**：缩略图墙是唯一的内容验收。
5. **大文件用轻量版验收**：主版只用于交付与归档。
6. **桌面只放主版一份**，同步后核 SHA256；原件与中间产物留在工作区。**每课只放一份成品**——内容接续的 PPT 必须合并重建进同一份 PDF，不按批次拆。例外：原件本身清晰可用就直接用原件，原件不可用才做整理版。
7. **裁切件是成品的唯一来源，不能单独删**：`课件清单.json` 的 `file` 指向 `照片裁切件N\`，删了就等于删掉重建能力（`build_all.py` 报 `FileNotFoundError`）。缺空间就把裁切件与清单**一起**归档，不要只删一半。误删只能重裁补齐，深色底的页还得再跑 `fix_blue.py`。
8. **重建前先核清单**：跑 `build_all.py` 之前确认「清单里每个 `file` 都存在」，比等它跑到一半报错快得多。

```powershell
& $py -c "
import json,os; base=r'<课程目录>'
d=json.load(open(os.path.join(base,'课件清单.json'),encoding='utf-8'))
miss=[it['file'] for it in d if not os.path.exists(os.path.join(base,it['file']))]
print('共',len(d),'缺',len(miss),miss[:5])"
```

## 目录

```
scripts/    10 个脚本（裁切 / 墙 / 清单 / 建册 / 合并 / 校验 / 入库），逐个说明见 references/scripts.md
references/photos.md    照片线算法、参数与判据
references/pptx.md      WPS COM / LibreOffice 转 PDF、合并、公式（OLE MTEF → PDF → OCR）
references/pdf.md       PDF 探测、OCR 分流、页标题清洗
references/verify.md    验收五条的命令与判据
references/ingest.md    入库三步、StudyHub 三档上限、OCR 缓存、_kb 目录分层
references/scripts.md   十个脚本干什么、依赖自检、跑完清理什么
references/pitfalls.md  踩过的坑（**卡住了先读它**）
```

## 附录：路径约定（跨机器可用）

本技能里的 `C:\deepseek\...` 与 `C:\Users\ZQY\...` 是作者机器上的实例路径；方法判据与下表配合，换台机器照样能跑：

| 符号 | 含义 | 作者机器实例 | 通用写法 |
|---|---|---|---|
| `DSH_HOME` | DSH 数据根 | `C:\Users\ZQY\.dsh` | `%USERPROFILE%\.dsh`（或环境变量 `DSH_HOME`） |
| `SKILLS_DIR` | 用户技能目录 | `C:\Users\ZQY\.agents\skills` | `%USERPROFILE%\.agents\skills` |
| `TOOLS_DIR` | 自建工具目录 | `C:\deepseek\tools` | 任选，固定后写回本表 |
| `WORK_DIR` | 工作区 | `C:\deepseek\work` | 任选 |
| `STUDY_DIR` | 学习资料 | `C:\deepseek\study` | 任选 |

换机器三步：①确认 `DSH_HOME`、`SKILLS_DIR`；②`scripts/` 里的常量在文件顶部，改成新路径再跑；③其余判据（版本号、报错串、行号）与具体路径无关，通常不用改。
