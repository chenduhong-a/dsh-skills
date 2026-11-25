# 脚本清单与依赖自检

## 十个脚本

| 脚本 | 干什么 | 对应流程 |
|---|---|---|
| `crop_portrait.py` | 照片裁切（批量、按可疑度排序） | 照片线 §1.2 |
| `fix_blue.py` | 深色底补光：裁切后对偏暗/偏蓝的页再跑一遍 | 照片线 §1.2 |
| `make_sheet.py` | 缩略图墙，目视验收用 | 照片线 §1.3 |
| `append_batch.py` | 向主清单追加本批，带文件重叠检测 | 照片线 §1.5 |
| `build_all.py` | 从清单重建三件套 PDF | 照片线 §1.6 |
| `build_pdf.py` | 合并 + 按连续同名分组写书签 | 照片线 §1.6 |
| `merge_pdfs.py` | PDF 线：把 PPT 转出来的多份 PDF 并成册 | PPT 线 §2.2 |
| `verify_order.py` | 抽 PDF 内嵌图像逐页比 SHA256 | 验收第 2 条 |
| `kb_ingest.py` | 入库到 `_kb\kb.sqlite`：`split` 体检 / `ingest` 灌库 | 入库 §4 |
| `kb_to_md.py` | 出库到 StudyHub：`kb.sqlite` 到按章 md | 入库 §4 |

**这里没有 `kb.py`**——那是 `_kb` 侧的查询 CLI，本技能不管查询，见 `references/ingest.md` 顶部那句。

## 依赖自检（每次开跑前 5 秒）

DSH runtime 升级会重置 `site-packages`——**装过的 cv2、pypdf 会悄悄消失**，脚本一跑就 `ModuleNotFoundError`。

```powershell
& $py -c "import cv2,pypdf,numpy,PIL,pypdfium2; print('ok', cv2.__version__, pypdf.__version__)"
```

报错就装（清华镜像，十几秒）：

```powershell
& $py -m pip install opencv-python-headless pypdf pypdfium2 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

Pillow 与 numpy 随 runtime 自带，通常不丢；**cv2 与 pypdf 是后装的，最容易没**。`pypdfium2` 也要装——`kb_ingest.py` 的 `has_text_layer()` 靠它判文字层，缺了会把所有 PDF 当扫描件。

## 工作目录

命令里的相对路径（清单、`--crop-dir`、`--src-dir`、`--seg`）一律按**清单所在目录**解析，不按当前 CWD。先 `cd` 到课程目录，或全部传绝对路径。

## 首次运行

`append_batch.py` 发现两个清单不存在会自动建空清单（`[]`）并打印提示，不用手工初始化。

## 跑完要清理什么

只删这些：`_tools\sheet*`（缩略图墙）、`work\_tmp` 下的临时件、切分后的 PDF 分片（`part_*.pdf`）、预览图。

**不要删 `照片裁切件N\`**——`课件清单.json` 的 `file` 字段指向它，删了就等于删掉重建 PDF 的能力（`build_all.py` 会直接 `FileNotFoundError`）。真缺空间就把裁切件与清单**一起**归档，不要只删一半。
