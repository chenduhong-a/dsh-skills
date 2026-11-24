# 验收：五条硬指标

成品出完不等于做完。**任何一条不过就不交付**。与 `SKILL.md` §5 同一套口径。

## 1. 页数

```powershell
# 图片清单（真相源）
(Get-Content 课件清单.json -Raw -Encoding utf8 | ConvertFrom-Json).Count

# PDF 实际页数
doc_info <成品.pdf>          # 看 pages
```

三个判据同时成立：清单条数 = PDF 页数 = 三件套各自页数。少一页就是丢页，多一页就是重复追加。

> 主版 >200 MB 时 `doc_info` 会拒绝，用轻量版验页数（页序完全相同）。

## 2. 顺序与字节（最强的一条）

```powershell
& $py <skill>\scripts\verify_order.py 课件清单.json 固体理论_课件整理.pdf
# → PDF 内嵌图像: 351 / 清单条目: 351
#   order + bytes identical: PASS
```

原理：`build_pdf.py` 用 DCTDecode 原样内嵌 JPEG，所以能把 PDF 里每个图像流的字节抽出来，逐页与清单图片做 SHA256。全等才说明**页序正确且画面没被重新编码**。

这一条比「渲染出来看看」强得多——它同时排除了顺序错、图片被换、编码失真。

## 3. 书签

`doc_info` 的 outline 顶层分组数要与分段表条数一致。

多批次累计成书时，`build_pdf.py:100` 只按连续同名分组，同一章被下一批续写在后面就会分成两个书签组 —— 这时**不要**要求「分组数 = 分段表条数」，改核「本批的每个分组名都在 outline 里」。

## 4. 抽页目视

至少要抽三页：**首批一页、中段一页、末页一页**。新批次还要抽批次交界的两页。

```
doc_render {path:"<轻量版>.pdf", pages:"263,300,351", scale:1.6}
read_image ...
```

看三件事：内容对不对得上批次边界、A4 居中排版是否正常、有没有整页空白（丢图）。

## 5. 哈希

```powershell
Get-FileHash 工作区\固体理论_课件整理.pdf -Algorithm SHA256
Get-FileHash 'C:\Users\ZQY\Desktop\课件PPT\固体理论\固体理论_课件整理.pdf' -Algorithm SHA256
```

两行必须一致。桌面只放主版一份，原件与中间产物留在工作区。

## 附：其它可查项

| 项目 | 命令 / 方法 | 期望 |
|---|---|---|
| 轻量版体积 | `Get-ChildItem` | 约主版的 1/7（q82 + 长边 2000） |
| 裁切质量 | `make_sheet.py` + `read_image` | 内容完整、无裁歪 |
| 深色底 | `fix_blue.py` 的 `_fixprev` 预览 | 红框贴住屏幕四边 |
| 磁盘占用 | `Get-ChildItem -Recurse \| Measure-Object Length -Sum` | 与本批体量相符（别忘 `_light_tmp` 已清） |

## 数字自检

统计体量时别用 `-f '{0:0.1}'`——PowerShell 里那是 .NET 自定义格式（`1` 是字面字符），94.1 MB 会印成「941 MB」。用 `{0:F1}`，并且**换一种口径再算一遍**（例如 `Measure-Object` 与 `Get-ChildItem` 两条路）。
