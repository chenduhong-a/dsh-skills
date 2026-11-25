# Office 文件篇

> 本文件是 `doc-parsing` 复合技能的一篇。分诊与选篇见上级 `SKILL.md`；PDF 与扫描件见同目录 `pdf.md`。
> **数据截止 2026-11-26**。带日期的实测数字见 `evidence/mineru-measurements.md` 第四节。
>
> 场景：从 docx / pptx / xlsx（含旧 `.doc` / `.ppt`）里取文本、表格、图片，以及 pptx 里的公式图（xlsx 的公式是 Excel 公式串不是 LaTeX，见 1.4）。与 PDF 不同，Office 是 zip + XML，坑集中在**结构与编码**，不在通道选择。
> **本文件只管读**：生成或编辑 Office 一律走 `univer` 系列（`univer-sheet` / `univer-doc` / `univer-slide`）。

## 开局

分诊见 `SKILL.md`「判据：先给文件分诊」（本节不再另立一张表，避免两处漂移）。先跑 `doc_info`（页/段/表统计）；pptx 再加 `doc_formulas action=scan`（只数 OLE 公式对象与 WMF/EMF，不渲染）。

## 1. 读 xlsx

### 1.1 自闭合单元格错位（最危险）

**症状**：读出一串有规律的怪值，差点据此作答。

**判据**：自闭合单元格 `<c r="D2" s="2"/>` 被朴素正则 `/<c r="([A-Z]+)\d+"([^>]*)>([\s\S]*?)<\/c>/g` 错位吞并——D2 本无内容，`[\s\S]*?` 一路吃到下一个 `</c>`，把 E 列值读成 D 列。

**处置**：显式区分自闭合：`/<c r="([A-Z]+)(\d+)"([^>]*?)(?:\/>|>([\s\S]*?)<\/c>)/g`。拿到表先核对列语义自洽：某列出现 8/11/14/17 这类等差怪值，就是错位信号。

### 1.2 用 openpyxl / python-docx 读（最常见的读法）

自己解包只为了看懂结构；真读表用库更快，但库有四个坑：

- `load_workbook(path, data_only=True)` 读公式单元格：文件里没有缓存值时返回 `None`（不是 0、也不是公式）。要公式本身用 `data_only=False`。
- `ws.max_column` / `ws.dimensions` 含脏区（编辑过又清空的格子永不缩小）——别按它定列数，按表头行实际有值的范围。
- 合并单元格只有左上角有值，其余是 `None`：用 `ws.merged_cells.ranges` 回填。
- 表头前有空行/标题行时 `header=0` 会偏移：先 `iter_rows(min_row=1, max_row=6)` 肉眼看一遍再定表头行号。

### 1.3 直接读 XML：空值 / 公式错

**判据**：`sharedStrings.xml` 要逐条按 `<si>` 拆，条内可能多个 `<t>`（富文本）需拼接；只取 `<v>` 不取 `<f>` 时，公式单元格拿到的是缓存值。

**处置**：按 `<si>` 切块后拼 `<t>`；要公式本身就读 `<f>`，要显示值才读 `<v>`。

### 1.4 xlsx 的公式不是 LaTeX（要 LaTeX 得自己转写）

**判据**：xlsx 单元格里的公式是 **Excel 公式语言**，存在 `<f>` 元素里（`<c><f>SUM(A1:A5)</f><v>15</v></c>`）——它既不是 MathType 的 MTEF、也不是 OMML 的 `<m:oMath>`，**没有 LaTeX 形态**。本技能后面第 3 节讲的公式提取全是 pptx 的 OLE 对象，**对 xlsx 不适用**（`doc_formulas` 只接受 `.pptx`）。

**处置**：三问分开——

| 要什么 | 怎么拿 |
|---|---|
| 公式原文（`=SUM(A1:A5)`） | 按 1.3 读 `<f>`，或用 `openpyxl.load_workbook(data_only=False)` |
| 算出来的值 | 读 `<v>`，或 `load_workbook(data_only=True)`（文件没存缓存值时返回 `None`，不是 0） |
| LaTeX | **只能自己转写**：`=SQRT(A1^2+B1^2)` 写成 `\sqrt{a^2+b^2}`。SUM / VLOOKUP / IF 这类业务函数转 LaTeX 没有意义，别做 |

**先问清是哪个**：用户说「提公式」时多半指前两种之一。判据——要排版就是 LaTeX，要核对计算就是值，要改表就是原文。

## 2. 读 docx

### 2.1 段落丢换行

**处置**：解包读 `word/document.xml`，`</w:p>` 转换行、`<w:tab/>` 转空格。

**公式范围**：docx 的公式若在文本层（`<m:oMath>` > 0），直接读 `<m:t>` 即可，**不走 §3 的 OLE 路径**（`doc_formulas` 只接受 `.pptx`）。也就是说本技能的公式提取只管 PPT；docx 里公式密集又不在文本层的，按 §4 转 PDF 再 OCR。

### 2.2 旧 `.doc`（Word 97-2003）

`python-docx` 读不了；转 PDF 再抽文字层最省事（§4），或 Word COM 打开另存。

## 3. 公式：先弄清存在哪一层

### 3.1 结构事实

**症状**：想直接读 PPT 里的公式，一试全是空。

**判据**：`<m:oMath>` 全为 0（14 个课件实测没有一个用公式编辑器录入）；公式是图——「高量1-矢量空间」54 页就 360 张图，`ppt/media` 里 319 个：315 个 `.wmf` + 3 个 `.emf`，其中 316 个带 MathType 标记（62 个带 DSMT）；但原始数据没丢，同一 pptx 里有 361 个 `ppt/embeddings/oleObject*.bin`，是标准 OLE 复合文档（`d0cf11e0` 头），内含 `Equation Native` 流（oleObject1.bin 的 offset 3072），即 MTEF v3 公式树，全库约 1243 个。

**处置**：只读 `a:t` 文本层的插件一律读不到（实测 dsh-office-tools 1.0.8 / dsh-pptx-sidebar 0.2.0 / dsh-pptx-editor 1.0.0 / pptx-viewer-mcp 2.10.1 全都只读文本层）。两条路都验证过、也都有代价：WMF 转 PNG 视觉读（矢量图型课件可用，**字体渲染型**课件会乱码）；解析 MTEF 出 LaTeX（准确但无可用现成解析器）。生产路径走 §3.3。

- **「有文字层就不用重跑 OCR」对 PPT 类文件是错的**：这类转出的 PDF 文字层常常只有标题与项目符号，公式、图表全在图片里——抽检汉字率可能只有个位数百分比（实测三份 PPT 转出的 PDF 只有 7.5%–28.2%）。判据不是「有没有文字层」，而是「该有的内容在不在文字层里」：挑一页含公式的，看公式符号能不能从文字层读出来。
- **矢量图的判据不能看形状和文件大小**：MathType 里 Greek χ 与 ASCII x 在 WMF 里长得一样、体积也一样；要按字体编码或 MathType 标记（DSMT 字串）判断，不靠观感。

### 3.2 两条已废弃的路，别重走

① 解析 MTEF v3：无公开规范、开源库只到 v5、字符码错位，约 10 轮未通。② WMF 转 PNG 拼 sheet 后视觉读：高量1 能读出 336 条，但**字体渲染型**课件上 `System.Drawing` 不认 MT Extra/Symbol（字体明明装着，GDI+ 照样不认），实测 10 个里 9 个乱码。

### 3.3 正解：LibreOffice 转 PDF 再 OCR

**判据/处置**：`--convert-to pdf`（54 页 3.9 秒）→ 逐页 OCR → 只取 `type=equation` 或 `label=Formula` 的块。高量1 实测 **67 个公式 / 32 页 / 40.8 秒**，LaTeX 质量好（Dirac 竖线偶尔识成 `\models`）。已落进 `doc_formulas`：`action=scan` 只数，`action=extract` 转 PDF + OCR；WMF 抽图死代码在 0.3.4 删除（mathtype.js 145 行）。

**先试 `action=extract`**（它就是这条路的封装）；只有要自定义 OCR 参数、页级坐标，或要图/表分离时才自己走命令行。页码基准：LibreOffice 一页一张 slide、无偏移，**PDF 页序 = slide 序号**。

## 4. Office 转 PDF：格式码与两个坑

**判据/处置**：COM 是 Windows 上最稳的一条路，格式码写死——Word 用 `Word.Application` + `SaveAs(path, 17)`（`17 = wdFormatPDF`）；PowerPoint 用 `PowerPoint.Application` + `SaveAs(path, 32)`（`32 = ppSaveAsPDF`）。

两个坑：

1. **`SaveAs` 成功后 `Quit()` 抛 `remote procedure call failed` 是正常现象**——文件已经存好了，别当成失败重跑。Quit 放 `try/finally`，异常只记不抛。
2. **Python 拼 PS 脚本时别用 `.format()`**——PS 代码里的 `{` `}` 会被当成占位符，报 `ValueError: unexpected '{' in field name`；改成字符串拼接（`'... "' + path + '" ...'`）。

真要跑时用这两段（可直接改路径）：

```powershell
# LibreOffice（装了就用它，不必开 Office）
& "C:\Program Files\LibreOffice\program\soffice.exe" --headless --convert-to pdf --outdir "$out" "$in"
```

```powershell
$app = New-Object -ComObject PowerPoint.Application
$pres = $app.Presentations.Open($in, $true, $false, $false)   # ReadOnly, Untitled, WithWindow
$pres.SaveAs($out, 32); $pres.Close()
try { $app.Quit() } catch { }   # Quit 报 RPC failed 属正常
```

WPS 用户换 ProgID：PowerPoint → `KWPP.Application`，Word → `Kwps.Application`。

另两条：批量前先杀残留的 `wpp` / `wps` / `winword` 进程，否则 COM 实例会抢文件——**杀之前确认没有未保存的文档**，那条命令不看内容直接结束进程。`.doc` 同理转 PDF 最省事。

## 5. 满屏 `□` 是私用区字符，不是字体缺失

**症状**：OCR 或转档出来的正文满屏 `□`，看着像「字体没装全」。

**判据**：查码位——`0xE000 <= ord(ch) <= 0xF8FF` 就是私用区（PUA）。私用区的意思是「某套字体的私有编码被当成 Unicode 存进了文本」，**一定有对应编码表可翻**，不要当字体缺失放着。实测一份群论库：115 种、41774 次、涉及 916 页，全是 Adobe Symbol 的私有编码（`U+F03D → =`、`U+F061 → α`、`U+F0E5 → ∑`、`U+F0C4 → ⊗`）；按 Symbol Encoding 建表后 112/115 种可映射、覆盖 41762 次。

**处置**：按字体编码建映射表批量替换，剩下映射不了的几种单独看。同一批还常见两处数据层残留——`['图6.19...']` 这类列表字面量（上游 `image_caption` 是 list，被 f-string 直接拼进正文），`<table>` 标签外露（`table_body` 是 HTML 未转文本），都是「上游字段类型没转」，清洗时一起过。

## 验收：什么时候算取对了

1. **行列与源一致**：列数对不上通常是合并单元格；拿到表先看有没有「等差怪值」（§1.1 的错位信号）。
2. **值的来源分清**：要显示值还是公式本身（`<v>` vs `<f>`），报告里说明按哪个口径取的。
3. **公式数量对得上**：`extract` 出的公式块数 ÷ 页数落在 0.5–5 之间属正常（样本：「高量1」67 个 / 32 页 ≈ 2.1，2026-11-26 实测，见 `evidence/mineru-measurements.md` 第四节；别的课件类型可能不同，别把它当阈值判据）；为 0 说明只走了文本层，>20 说明把正文块也当公式抓了。
4. **抽 2–3 段原文逐字比对**：错字允许，改内容、漏段、串行不可接受。
5. **`□` 要说是编码问题还是真缺字**：查码位（§5），别把私用区当字体缺失交付。
6. **导出的 PDF 对得上**：页数 = slide 数（或段落页数）、中文字体已嵌入（否则手机上显示方框）、体积适合手机翻看。

## 什么时候停（停止条件）

- **同一通道连试两次都失败** → 换通道（OOXML 直读失败转 COM，COM 失败转 LibreOffice 转 PDF），别在同一条路上试第三次。
- **读表出现等差怪值** → 先停，按 §1.1 修正则重读，别在那张表上继续推断。
- **`Quit()` 报 RPC failed** → 文件已存好，不要重跑（§4）。
- **公式只出编号** → 是 formula 开关或通道没对（文本层），换 §3.3 的路，不要在文本层反复调参。

> 路径符号（`DSH_HOME` / `SKILLS_DIR` / `MINERU_VENV` 等）统一见 `SKILL.md` 附录；正文里出现的绝对路径只是作者机器实例，换机器按符号替换，判据与路径无关。

