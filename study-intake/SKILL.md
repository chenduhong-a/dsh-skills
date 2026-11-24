---
author: "ZQY-LB"
name: study-intake
description: "把一门课散落的课件整理成一份能翻能查的成品 PDF，并送进知识库（可选送 StudyHub）——手机翻拍的投影幕照片、原始 .ppt/.pptx、扫描版或矢量 PDF 三类来料各有流程。当用户说「我又放了一批课件」「这批照片帮我整理」「把课件入库」「这个 PDF 怎么进库」时使用。不用于出题、出学习总结与复习资料（见 study-flow）、只解析某一页取文本（见 doc-parsing）、编辑 Word/Excel/PPT 成品（见 univer 系列）。"
---

# 课件入库（study-intake）

> 版本号见 `CHANGELOG.md` 顶部（当前 1.2.0）。frontmatter 里不写 `version`——技能加载器不读它。

把「一堆原始文件」变成「一份带书签的成品 PDF + 可检索的正文」，中间每一步都能被目视或哈希验证。
**出题、出学习类 PDF 不归这里**——那是 `study-flow` 的事，本技能到「入库」为止。

## 运行前：把两个符号设成你的

下面所有命令块里的 `$py` 与 `$skill` 是本机路径，**照抄前先在当前 PowerShell 里设一次**：

```powershell
# python 解释器：要能 import cv2 / pypdf / pypdfium2 的那只（本机是 DSH 运行时自带的，见 §8 自检）
$py    = '<你的 python 可执行文件>'
# 本技能自己所在的目录
$skill = '<你的 skills 根>\study-intake'
```

其余占位符按当次实际填：`<课程>` = 这门课的资料目录名；`<成品.pdf>`、`<临时目录>` 见各命令的上一句。
两个变量没设就照抄，报的是「找不到文件」或 `ModuleNotFoundError`——那不是脚本坏了。
还有个库路径：`scripts\kb_ingest.py` 与 `kb_to_md.py` 的默认值是作者机器上的 `C:\deepseek\study\_kb\kb.sqlite`，你的库在别处就先 `$env:STUDY_KB_DB = '<你的 kb.sqlite 路径>'`，否则报 `unable to open database file`。

## 0. 先判来料，选入口

| 来料 | 典型形态 | 走哪条线 |
|---|---|---|
| 手机翻拍投影幕 | `IMG_YYYYMMDD_HHMMSS.jpg` 几百张，尺寸 4320×5760 | **照片线**（§1） |
| 原始 PPT | `.ppt` / `.pptx`，一讲一个文件 | **PPT 线**（§2） |
| PDF | 扫描书、矢量教材、别人给的讲稿 | **PDF 线**（§3） |

三条线最后都汇到**入库**（§4）与**验收**（§5）。判断依据只有一条：**原件是否「清晰可用」**——清晰可用就放原件，不可用（照片、版本混乱、PPT 转不成 PDF）才做整理版。

## 1. 照片线：翻拍照片 → 三件套 PDF

### 1.1 归置批次
文件名里有时间（`IMG_20261104_080136.jpg` = 11-04 08:01:36），**按这个分批次、排顺序，不看文件修改时间**。
先读首末两张判断内容接续：接上一批就并进同一本，开新章就新起一段。

```
<课程>\照片原件N\      ← 原始照片，零修改
<课程>\照片裁切件N\    ← 裁切产物，文件名与原件同名
<课程>\课件清单.json           ← 主版清单（裁切件）
<课程>\课件清单_未裁剪.json     ← 未裁剪版清单（原件）
```

### 1.2 裁切
```powershell
$py = '<你的 python 可执行文件>'   # 见「运行前」
& $py $skill\scripts\crop_portrait.py 照片原件5 照片裁切件5
```
深色底（深蓝/深绿幻灯片）会被灰度判据吃掉，只有白块留下来——**先看报告里的 `areaPct`，低于 15% 的看是不是这种；宽高比 <1.0 或 >2.0 的也会单独列「可疑」**（竖拍裁完应是 1.0–2.0 之间），用 `fix_blue.py` 重裁并看预览红框：
```powershell
& $py $skill\scripts\fix_blue.py 照片原件5 照片裁切件5 IMG_20261104_104519.jpg IMG_20261104_111007.jpg
```
算法与判据见 `references/photos.md`。

**灰度判据遇深蓝底会失效**：投影幕照片若是深蓝/深绿底色，按灰度找亮区会把整片背景当成内容。加一路饱和度判据（背景高饱和、幕布低饱和）或先在 HSV 里把 S 通道切掉再算。只调灰度阈值调不出来。

### 1.3 目视验收：缩略图墙
```powershell
& $py $skill\scripts\make_sheet.py 照片裁切件5 _tools\sheet 5
```
生成 5×4 的墙，**逐墙 `read_image` 看**：内容是否完整、有没有裁掉半行、有没有把观众人头当屏幕。这一步不能省——算法指标只能排序可疑度，不能替代眼睛。

**缩略图墙的页码标签靠脚本打，不能数格子**：靠数格子对应页码在 40 张以上必错（裁切后长宽比不一，网格会错位）。`make_sheet.py` 实际用 `cv2.putText` 把「序号 + 文件名前 19 字符」画在**每格下方**（文本 `'%02d %s' % (i+1, f[5:24])`，文件名前 5 字符被截掉），验收时直接看图上的号。

### 1.4 定分段
看完墙才知道这一批跨了哪几节。写成分段表：`时间段 → 分组名`，颗粒度对齐「章 › 节」。
```json
[["080136", "第四章 晶体缺陷 › 点缺陷与缺陷团簇（11-04 续）"],
 ["080354", "第四章 晶体缺陷 › 线缺陷：位错"]]
```
新批次**标题一律先写「第 N 页」占位**，精修另做；测边界时先给 2～3 个候选起点各跑一遍，用 `--dry-run` 看每个起点归到哪一组，别只试一个。

### 1.5 追加清单
```powershell
& $py $skill\scripts\append_batch.py --manifest 课件清单.json --raw-manifest 课件清单_未裁剪.json `
    --crop-dir 照片裁切件5 --src-dir 照片原件5 --seg seg.json [--dry-run]
```
它会：先备份 `.bak_<时间戳>` → 校验两目录张数一致 → 追加 → 只在**本批范围**内把「第 0 页」改成真实页号（老条目的真标题绝不覆盖）→ 打印本批分组分布。

### 1.6 重建三件套
```powershell
& $py $skill\scripts\build_all.py --dir . --name 固体理论 `
    --cropped 课件清单.json --raw 课件清单_未裁剪.json
```
产出主版 / 轻量版（长边 2000、q82）/ 未裁剪版，页数必须三者相同。

## 2. PPT 线：原始 PPT → 合并册

### 2.1 转 PDF
WPS COM，**一个文件一个实例**（同一实例转第二个必崩 `0x800706BA`）：
```powershell
$wps = New-Object -ComObject Kwpp.Application
$pres = $wps.Presentations.Open($src, $false, $false, $false)
$pres.SaveAs($out, 32)   # 32 = ppSaveAsPDF
$pres.Close(); $wps.Quit(); Start-Sleep -Milliseconds 800
```
`.ppt`（旧二进制）插件读不了，先转 PDF 再谈入库。
- 公式密集、或后面要 OCR 的课件，用 LibreOffice 转更省事：`& 'C:\Program Files\LibreOffice\program\soffice.exe' --headless --convert-to pdf`（**裸 `soffice` 不在 PATH**，本机 26.8.2.2；实测 54 页 3.9 秒；不加 `--headless` 会弹 GUI）。WPS COM 那条路仍按上面「一文件一实例」走。

### 2.2 合并加书签
```powershell
& $py $skill\scripts\merge_pdfs.py --out 高等量子力学_课件整理.pdf --dir _pdf `
    --pattern '^高量(\d+)-(.+)\.pdf$' --label '第{n}讲  {t}' --title '高等量子力学 课件整理'
```
输出末尾必须报「页数合计 / 体积 / 每讲起始页」，与各文件页数相加对得上。

### 2.3 公式（只有 PPT 里有 MathType 公式时才做）

MathType 公式是 **OLE 嵌入对象**，不是 Office 公式：`ppt/embeddings/oleObject*.bin` 内含 `Equation Native` 流（MTEF v3），`<m:oMath>` 全库为 0；现成插件只读 `ppt/slides/slideN.xml` 的 `a:t` 正文层，公式拿不到。

`doc_formulas action=scan` 先数一遍（oleObject 数 + WMF/EMF 分布）→ `doc_formulas action=extract` 出 LaTeX（内部走 **LibreOffice `--convert-to pdf` → 逐页 OCR**，只取 `type=equation` 或 `label=Formula` 的块，带页码）。实测高量1：67 个公式 / 32 页 / 40.8 秒。

- **WMF/EMF 抽图路线已弃用**：这类公式图是字体渲染型，`System.Drawing` 不认 MT Extra/Symbol，10 个课件里 9 个出乱码字形。
- **别解 MTEF**：无公开规范、开源库只到 v5，约 10 轮未通、字符码错位（读出 U+0200 而实际是 ψ）。
- 细节与校验见 `references/pptx.md`。

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

**页标题是入库质量的一半**：扫描教材的页标题清洗有四个坑（目录白名单、页首双条件、章号只增不减、跳过前 20 页），做法见 `references\pdf.md` 末节「页标题清洗」。

## 4. 入库

> **知识库插件 `@local/dsh-knowledge-base` 已于 2026-11-16 卸载**：该插件提供的 `kb_*` 工具全部不可用（已卸），文中引用一律按「已卸」读。下面走的是技能自带的 `scripts\kb_ingest.py` / `kb.py` / `kb_to_md.py`——直接读写 `_kb\kb.sqlite`，不依赖插件。

| 目标 | 手段 | 判据 |
|---|---|---|
| 知识库 `_kb` | `scripts\kb_ingest.py`，三步：`split` 体检 → `doc_ocr` → `ingest` | `kb.py find <词> --course <课>` 能命中，`kb.py page <doc> <seq>` 能取原页 |
| StudyHub 材料（可选） | `scripts\kb_to_md.py` 生成 md → `document.import`（PDF ≤ 200 页、文件 ≤ 8 MB） | `source.list {course, groupBy:"document"}` 的 total 等于生成份数 |
| StudyHub 题目（可选） | 已有题用 `document.import` / `deck.import` | decks/cards 计数变化 |

**完整命令、三条硬坑（字节闸 `209715200` / OCR 缓存路径 / 写完必须重建 FTS）与「为什么走 md」都在 `references/pdf.md` 第五节。** StudyHub 两条是可选的：不装它时只做上一行「入库 `_kb`」，用 `kb.cmd find` / `kb.cmd page` 查（`kb.cmd` 是 `_kb` 根下的固定入口，硬编码 `%~dp0app\kb.py`，优先 `%~dp0py\Scripts\python.exe`、回退 runtime python；本机没有 `config.json`）。自学线（`study-flow`）不依赖 StudyHub，也不读它的数据——两条线各走各的。

## 5. 验收（五条不过就不交付）

细则与命令在 `references/verify.md`，两处口径一致。

1. **页数**：`doc_info` 的 pages 与清单条数相等；三件套三者相等。
2. **顺序与字节**：`scripts\verify_order.py` 抽 PDF 内嵌图像逐页与清单图片比 SHA256，必须 `order + bytes identical: PASS`——一条同时排除顺序错、图被换、编码失真。
3. **书签**：`doc_info` 的 outline 顶层分组数与分段表一致（多批次成书时只核「本批分组都在」）。
4. **抽页目视**：首批一页、中段一页、末页一页，`doc_render` 渲染后 `read_image`——内容必须对得上批次边界。
5. **哈希**：桌面副本与工作区成品 SHA256 一致（`Get-FileHash`）；先 `Copy-Item` 过去再比。

主版常超 200 MB，`doc_render` / `doc_info` 会报 `file too large (>209715200)`——**页数与抽页目视**用轻量版（它和主版只差分辨率，页序完全相同）；但**顺序与字节、哈希必须用主版**。轻量版把 JPEG 重编码成 2000/q82，字节必然不同，拿它跑 `verify_order.py` 只会得到 `MISMATCH`（实测主版 PASS、同一清单轻量版 FAIL 3 处）。

## 6. 八条不变量

1. **原件不动**：`照片原件N` 只读，所有裁剪写到 `照片裁切件N`。
2. **先备份再改清单**：任何清单写入前 `.bak_<时间戳>`。
3. **只在新增范围内改标题**：老条目的真标题绝不被「第 N 页」覆盖。
4. **算法只排可疑度，验收靠眼睛**：缩略图墙是唯一的内容验收。
5. **大文件用轻量版验收**：主版只用于交付与归档。
6. **桌面只放主版一份**，同步后核 SHA256；原件与中间产物留在工作区。**每课只放一份成品**——内容接续的 PPT 必须合并重建进同一份 PDF，不按批次拆，新批并进主文件后把分批产物删掉。例外：原件本身清晰可用就直接用原件（如高量），原件不可用（照片翻拍、乱文件）才做整理版。
7. **裁切件是成品的唯一来源，不能单独删**：`课件清单.json` 的 `file` 字段指向 `照片裁切件N\`，删掉裁切件目录等于删掉重建 PDF 的能力——`build_all.py` 会直接报 `FileNotFoundError: …照片裁切件/IMG_xxx.jpg`。工作区紧张时只删 `_tools\sheet*`、`work\_tmp`、切分后的 PDF 分片与预览图；**要腾大空间就把裁切件与清单一起归档**，不要只删一半。误删后只能按 `crop_portrait.py` 重裁补齐，深色底的页还得再跑一遍 `fix_blue.py`。
8. **重建前先核清单**：跑 `build_all.py` 之前先确认「清单里每个 `file` 都存在」，比等它跑到一半报错快得多。

```powershell
& $py -c "
import json,os; base=r'C:\deepseek\<课程>'
d=json.load(open(os.path.join(base,'课件清单.json'),encoding='utf-8'))
miss=[it['file'] for it in d if not os.path.exists(os.path.join(base,it['file']))]
print('共',len(d),'缺',len(miss),miss[:5])"
```

## 7. 知识库目录分层（2026-11-19 定）

`_kb\` 按用途分组，根目录只留入口与数据——二十七项混放时用户原话「这个看着好乱」：

```
_kb\
├─ kb.cmd  kb.sqlite  README.md  _cache\   ← 入口、库、页面缓存
├─ app\       8 个脚本（kb.py / add_book / index_vec / reocr_indra / embed / kb_textlayer / export_md / download_model）
├─ docs\      勘误三件 + README_插件缓存.md + formulas\ 公式表
├─ models\    bge-small-zh —— ask 的运行依赖，不是缓存，删了 `kb.py ask` 直接瘫
├─ backup\    旧库 + code_before_move\ 代码原件
└─ digest\    5 门课的摘要素材（KaTeX 等前端资源在 pdf 插件里，_kb 下没有 vendor\）
```

搬动后要跟着改的三处：①脚本里取同目录资源用 `APP = os.path.dirname(os.path.abspath(__file__))`，不要拿 `KB` 拼脚本名；②`embed.py` 的 `MODEL_DIR` 与 `index_vec.py` 的 `DB` 上跳一级（`dirname(dirname(__file__))`）；③`kb.cmd` 指向 `app\kb.py`，不要指向根。改完把 `kb.cmd status`、`kb.py find`、`kb.py page`、`index_vec.py`、`kb.py check` 各跑一遍再算完成。

## 8. 依赖自检（每次开跑前 5 秒）

DSH runtime 升级会重置 `site-packages`——**装过的 cv2、pypdf 会悄悄消失**，脚本一跑就 `ModuleNotFoundError`。

```powershell
$py = '<你的 python 可执行文件>'   # 见「运行前」
& $py -c "import cv2,pypdf,numpy,PIL,pypdfium2; print('ok', cv2.__version__, pypdf.__version__)"
```

报错就装（清华镜像，十几秒）：

```powershell
& $py -m pip install opencv-python-headless pypdf pypdfium2 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

Pillow 与 numpy 随 runtime 自带，通常不丢；**cv2 与 pypdf 是后装的，最容易没**。

## 9. 目录

```
scripts/                    可直接调用的脚本，用 $py 的绝对路径执行
scripts/crop_portrait.py    照片裁切（批量、按可疑度排序）（1.2）
scripts/fix_blue.py         深色底补光：裁切后对偏暗/偏蓝的页再跑一遍（1.2）
scripts/make_sheet.py       缩略图墙，目视验收用（1.3）
scripts/append_batch.py     向主清单追加本批，带文件重叠检测（1.5）
scripts/build_all.py        从清单重建三件套 PDF（1.6）
scripts/build_pdf.py        合并 + 按连续同名分组写书签（1.6）
scripts/merge_pdfs.py       PDF 线：把 PPT 转出来的多份 PDF 并成册（2.2）
scripts/verify_order.py     抽 PDF 内嵌图像逐页比 SHA256（5 的第 2 条）
scripts/kb_ingest.py        入库到 _kb\kb.sqlite：split 体检 / ingest 灌库（4）
scripts/kb_to_md.py         出库到 StudyHub：kb.sqlite 到按章 md（4）

references/photos.md        照片线算法、参数与判据
references/pptx.md          WPS COM / LibreOffice 转 PDF、合并、公式（OLE MTEF 到 PDF 到 OCR）
references/pdf.md           PDF 探测、OCR 分流、入库完整命令（第 4 节的详细版）
references/verify.md        验收五条的命令与判据
references/pitfalls.md      踩过的坑（建议先读一遍）
```

**工作目录**：命令里的相对路径（清单、`--crop-dir`、`--src-dir`、`--seg`）一律按**清单所在目录**解析，不按当前 CWD——先 `cd` 到课程目录，或全部传绝对路径。

**首次运行**：`append_batch.py` 发现两个清单不存在会自动建空清单（`[]`）并打印提示，不用手工初始化。

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

换机器三步：①确认 `DSH_HOME`、`SKILLS_DIR`、`NODE_BIN`；②`scripts/` 里的常量在文件顶部，改成新路径再跑；③其余判据（版本号、报错串、行号、端口规则）与具体路径无关，通常不用改。