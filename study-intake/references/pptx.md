# PPT 线：原始 PPT → 合并册（+ 公式：LibreOffice 转 PDF + OCR）

## 一、先看格式

- `.pptx` 是 zip，插件能直接读。
- `.ppt` 是旧二进制，**任何按 zip 解的工具都会报 `File is not a zip file`**。先转成 PDF（§二）再谈别的。

判断方法：`Get-Content <file> -TotalCount 1 -AsByteStream`（PowerShell 7.x；5.1 才用 `-Encoding Byte`，7.x 下会报 `'Byte' is not a supported encoding name`）——PK 开头是 pptx，`D0 CF 11 E0` 是旧 ppt。

## 二、WPS 转 PDF

```powershell
$wps = New-Object -ComObject Kwpp.Application
$pres = $wps.Presentations.Open($src, $false, $false, $false)
$pres.SaveAs($out, 32)      # 32 = ppSaveAsPDF
$pres.Close()
$wps.Quit()
Start-Sleep -Milliseconds 800
```

三个坑：

1. **一个文件一个实例**。同一实例转第二个必崩：`The RPC server is unavailable (0x800706BA)`。早期是第 5 个才崩，后来第 2 个就崩——别赌能连开几个。
2. **不要设 `$wps.Visible = $false`**，会抛 `E_FAIL`。默认就是不可见的。
3. 批量转换用 `PowerShell -EncodedCommand` 传 UTF-16LE Base64，避免中文路径被命令行吃掉；一文件一进程。

## 三、合并加书签

```powershell
& $py <skill>\scripts\merge_pdfs.py --out 高等量子力学_课件整理.pdf --dir _pdf `
    --pattern '^高量(\d+)-(.+)\.pdf$' --label '第{n}讲  {t}' --title '高等量子力学 课件整理'
```

`pattern` 第一组是排序键、第二组是标题；没有捕获组就按文件名排序、标题取文件名。输出会打印每讲页数与起始页，**加起来必须等于总页数**。

书签是顶层一级（每讲一条），够用；要实现「讲 → 节」两级，得改 `merge_pdfs.py` 里的 `add_outline_item` 加 parent。

## 四、公式（只在 PPT 里有 MathType 公式时做）

### 4.1 它们是什么

不是 Office 公式（`<m:oMath>` 全库为 0）。是 MathType 的：

- `ppt/embeddings/oleObject*.bin` —— Equation Native / MTEF v3 二进制
- `ppt/media/*.wmf` —— 对应的矢量图

**别试着解 MTEF**。试过 olefile + MTEF 补丁，字符码错位且没有公开规范；开源库（MTEF-py-FIX）按 v5 实现，v3 的 LINE/CHAR/TMPL 布局不同，约 10 轮未通（读出 U+0200 而实际是 ψ）。

**现成插件只读 `a:t`，公式只能走「LibreOffice 转 PDF + OCR」**：`dsh-office-tools` / `dsh-pptx-sidebar` / `dsh-pptx-editor` / `pptx-viewer-mcp` 全都只读 `ppt/slides/slideN.xml` 的 `a:t` 文本层，公式在 `a:t` 里根本不存在。

**WMF/EMF 抽图路线已弃用**：这类图是字体渲染型，`System.Drawing`/GDI+ 画文本记录时不认 MT Extra/Symbol（字体明明装着），实测 **10 个课件里 9 个变乱码字形**。正解是 LibreOffice `--convert-to pdf`（54 页 3.9 秒）再逐页 OCR，只取公式块；0.3.4 起 `doc_formulas` 已删掉 WMF 抽图的死代码（`mathtype.js` 145 行）。

### 4.2 三个工具

| 工具 | 作用 |
|---|---|
| `doc_formulas action=scan` | 报每页 oleObject / wmf 数、预计图块数 |
| `doc_formulas action=extract` | LibreOffice 转 PDF → 逐页 OCR → 只回公式块 LaTeX（带页码） |
| `doc_formulas action=stats` | 当前文件的公式缓存体积 |
| `doc_formulas action=clean` | 清缓存（要 `confirm=true`） |

extract 直接给每页的公式块 LaTeX，不再拼「一页一张竖长图」；旧的 sheets 缓存（`$DSH_HOME\storages\pptx-formula\<sha16>\sheets\`）只用于回看历史稿，新活不再产生。

### 4.3 判同源，别重复劳动

同一节课常有 2023 / 2024 / 2025 三个版本。**先算逐页公式图数序列**：

```
2023: [2,0,1,1,2,6,1,2,1,3,2,3,5,2,0,0,2,5,3,6,6,6,6,6,7,6,5,7,8,3,4,8,4,0]
2025: 仅 p12 3→2、p21 6→7、p29 8→6、p30 3→4 不同
```

序列几乎一致 = 同一套课件，**只转录最新那一版**，其余跳过。这一条能省掉一半工作量。

### 4.4 校对与抽查

`extract` 已直接给 LaTeX，剩下的活是**抽查**而不是逐张转录。

- 随手挑 5 条回原页对（`doc_render` 渲该页，或看 PPT 原页），重点看花体、上下标重叠、分式嵌套。
- 已知偏差：Dirac 竖线偶尔被识成 `\models`。
- 只取 `type=equation` 或 `label=Formula` 的块，正文文字混进来的要剔掉。

产出按页号分节，每条保留原页号做定位注释：

```markdown
### 第 4 页
1. $[\chi(a)\chi(b)]\chi(c)=\chi(a)[\chi(b)\chi(c)]$
```

### 4.5 校验

- 每条都能在 PPT 原页找到对应位置
- **别拿 scan 的计数当等式**：scan 报的 oleObject / WMF 数含非公式的嵌入对象与装饰性图形——高量1 实测 361 个 oleObject、OCR 只出 67 条公式。校验用「有公式的页码逐页点过 + 抽查」，不用相等关系
- 同一公式在 slide XML 里可能出现两次（一条 VML 备用、一条带 `<p:pic>` 真图），按 oleObject 名去重、保留带图那条
- `doc_formulas action=stats` 报的缓存体积与本批页数相符
