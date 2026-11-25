# CHANGELOG

## 1.2.2 — 2026-11-26 · 独立诊断报告指出的三处悬空引用

三份技能诊断报告（`C:\deepseek\调研\技能梳理\`）里有三条经我逐条复核为真，全在「照文档做就失败」这一档：

- **声称有 `scripts\kb.py`，实际没有**：`SKILL.md` §4 的引言把 `scripts\kb_ingest.py` / `kb.py` / `kb_to_md.py` 并列成「技能自带」，`DEPENDENCIES.md:6` 又写了一遍；`Test-Path` 实测 False，`scripts\` 下只有 10 个 `.py`。而同一份 `DEPENDENCIES.md:13` 自己又说查询入口是 `_kb\kb.cmd`——两个位置互相打脸。已改为「入库用 `kb_ingest.py`、转 md 用 `kb_to_md.py`，**查询不在本技能里**，用 `_kb\kb.cmd`」。
- **§4 判据列的 `kb.py find` 跟着改**：`kb.py find <词> --course <课>` → `kb.cmd find ...`，`kb.py page` → `kb.cmd page`。同节末尾本来就写着「不装 StudyHub 时用 `kb.cmd find`」，两处口径现在一致。
- **§5 末句「主版常超 200 MB」与判据对不上**（诊断报告未提，我顺手核的）：`doc_render` / `doc_info` 的硬闸是 `209715200` B，而主版实测 853.7 MB——「常超」没错，但少了「超了会报什么」，补了报错原文 `file too large (>209715200)`。

未采纳：报告建议把 `SKILL.md` 从 262 行压到 ≤250 行、把 §7 `_kb` 分层与 §8 依赖自检移出、`CHANGELOG` 搬进 `evidence/`。这三条是结构重排，涉及与其他技能的边界重新划分，先挂账。

## 1.2.1 — 2026-11-25 · 固体 510 页入库踩出的两个坑

真实任务：固体理论课件整理从 456 页增到 510 页，要重灌知识库。这份 PDF 是照片拼的、没有文字层，只能走 OCR，于是把两个一直没被触发过的缺陷全踩了出来。

- **`split` 的体检只看体积，不看页数**：它输出「无文字层，但 116.1 MB ≤ 190 MB → 整份跑 doc_ocr」，照做立刻被在线 API 拒：`number of pages exceeds limit (200 pages), please split the file and try again`。**体积阈值与页数上限是两个独立判据**，之前的代码只查了前者。新增常量 `OCR_MAX_PAGES = 200`（MinerU 在线硬限），`cmd_split` 改成两个都查，页数超限时明确打印「必须切片（体积够小也一样）」。实测同一份 PDF 现在正确报「页数 510 > MinerU 在线上限 200 页 → 必须切片」并给出 6 份切分件。
- **`text_via_cache` 缺页时静默跳过，导致标题整段错位**：OCR 有三页失败（都是黑板板书，MinerU 返回 `page missing in online result`），旧代码只 append 成功的页，函数返回 507 条正文配 510 条标题，`cmd_ingest` 只打一句「页数与标题条数不一致，改为按页序截断」就继续——结果第 36 条 items 装的是原页 37 的正文却配了清单第 36 条的标题，**从第一个缺页起全部错位**，而入库回执只说「已写入 507 条」，看不出来。
  - 改成：缺页 append 空串占位（保持与页序一一对应），并返回缺页的原页号列表；`cmd_ingest` 打印 `N 页没有 OCR 结果，正文留空但保留页序：[36, 193, 222]`。这样标题天然对齐，缺页在 items 里是「有标题、正文空」的条目，事后能定位。
- **踩到的正解**：`CHUNK_PAGES = 100` 与 `OCR_MAX_PAGES = 200` 不是一回事——前者切分件的体积依据（照片类约 1.6 MB/页），后者是 API 页数硬限。手造 200 页片虽然能过 API，但与 `split_pdf()` 生成的 `part_{start+1}-{end}.pdf` 哈希不同，OCR 缓存不命中；**要让缓存命中就必须按脚本自己的规则切**。

## 1.2.0 — 2026-11-22 · 独立审查员修出 12 条（1 条同源追加）

审查方式：派一个只读子代理，给它技能目录与「把 280 张课件照片整理成册并入知识库」的真实任务，要求只读、不写库、不装包、每条证据必须真跑过。它实测了 20 个文件 / 10 个脚本 / 26 条命令，报 12 条（P1 2 / P2 10）。特别核查两项**通过**：`append_batch.py` 的重叠检测（上一版新加的）三态都对；`verify.md` 五条与 `SKILL.md` §5 的条数与内容一致。

- **P1 「验收一律用轻量版」与五条验收第 2/5 条冲突**：轻量版把 JPEG 重编码为长边 2000/q82，字节必然不同——同一清单实测主版 `order + bytes identical: PASS`、轻量版 `MISMATCH page 1/2/3` + `FAIL (3 处)`。三处（`SKILL.md` §5 末、`pdf.md` 第 98 行、`pitfalls.md` 第 39 行）改成「**页数与抽页目视**用轻量版；**顺序与字节、哈希必须用主版**」。
- **P1 `kb_ingest.py` 默认 dry-run 先写库**（上一版「自动建课程」引入的）：建课程带 `commit()`、`split_pdf()` 写切分件，两者都在 `if not args.go` 之前。现在 dry-run 只读：课程不存在只提示「--go 时自动建」，OCR 路径直接打印「dry-run 不切分、不写盘」并返回，不碰磁盘不碰库。实测 courses 5→5。
- **`append_batch.py --dry-run` 会建空清单**（与 docstring「不写盘」相反）：`load_list()` 加 `create` 参数，调用处传 `create=not a.dry_run`。三态实测：dry-run 两清单都不建、打印「清单不存在（dry-run 不建）」且分组照常输出；不加 `--dry-run` 仍正常建并写入。
- **`kb_ingest.py` 的验证命令指向不存在的 `_kb\kb.py`**：改成 `kb.cmd find <关键词> --course X`（`kb.cmd` 是 `_kb` 根下入口，转发到 `app\kb.py`）。
- **`SKILL.md` §7 目录分层与实测不符**：`app\` 是 8 个脚本不是 11 个（`kb.py` / `add_book` / `index_vec` / `reocr_indra` / `embed` / `kb_textlayer` / `export_md` / `download_model`）；`_kb\vendor` 不存在，`digest` 在 `_kb` 根下、内含 5 门课的 md。
- **`SKILL.md` 「`kb.cmd` 路径写在 `config.json`」**：本机根本没有 `config.json`；`kb.cmd` 硬编码 `%~dp0app\kb.py`，优先 `%~dp0py\Scripts\python.exe`、回退 runtime python。
- **`photos.md` 的「`areaPct < 15%` 且 `ratio > 3`」是联合判据，代码里不存在**：`crop_portrait` 报告里 small_ones 与 ratio 可疑是两张独立表。拆成两行并注明「没有联合判据」。
- **`SKILL.md` 「缩略图墙用 PIL 打页码标签」**：`make_sheet.py` 实际用 `cv2.putText` 画在**每格下方**，文本 `'%02d %s' % (i+1, f[5:24])`（文件名前 5 字符被截掉）。改成描述实际行为。
- **宽高比阈值两套说法**：`SKILL.md` 说 `>3` 才可疑，`crop_portrait.py:86` 实际是 `<1.0 或 >2.0`。改成「低于 15% 的看是不是深色底；宽高比 <1.0 或 >2.0 也单独列可疑（竖拍裁完应在 1.0–2.0 之间）」。
- **`pitfalls.md` 的重装命令漏 `pypdfium2`**：这是全套里最隐蔽的一条——`has_text_layer()` 内 `import pypdfium2` 失败会 `return False`，**有文字层的 PDF 被静默当成扫描件走 OCR**。命令补上包名，`has_text_layer()` 的 `except ImportError` 也改成先打印警告再返回（否则读者只看到「路径：OCR 缓存」，以为 PDF 本来就没文字层）。
- **`pptx.md` 的 `-Encoding Byte` 在 PowerShell 7.x 直接报错**（`'Byte' is not a supported encoding name`）：改成 `-AsByteStream`，并注明 5.1 才用旧参数。
- **`SKILL.md` 用裸 `soffice`**：不在 PATH（`Get-Command soffice` 为空），实际在 `C:\Program Files\LibreOffice\program\soffice.exe`（26.8.2.2），且不加 `--headless` 会弹 GUI。

## 1.1.0 — 2026-11-21 · skill-authoring 自足性验收修的 7 条

自足性验收方式：派一个只有「技能目录 + 一句任务」的独立子代理跑真实场景（280 张课件照片整理成 PDF 再入库），把它卡住的地方当判据缺口，再回改。

- **`append_batch.py` 承诺的防重复校验根本不存在（最危险）**：`pitfalls.md:31` 说「追加前会校验目录与清单是否已重叠」，实际脚本只比 `crop_dir` 与 `src_dir` 两个目录的数量与文件名，**完全不看主清单已有条目**——同一批跑两次会静默重复。现在加真检测：建 `have = {it.get('file')}`（含反斜杠归一），命中就 `sys.exit` 并提示先查 `.bak_<时间戳>` 回滚；确认要重复才加新参数 `--allow-dup`。三态实测通过（首次写入 2 张 / 同批再跑 rc=1 中止 / 加 `--allow-dup` 继续）。
- **首次运行会 `FileNotFoundError`**：两个清单不存在时 `json.load(open(...))` 直接崩。新增 `load_list()`，不存在就建空清单 `[]` 并打印提示。
- **`--seg` 按 CWD 解析，而 `--crop-dir` / `--src-dir` 按清单目录解析**：同一条命令里两种基准。现在三个路径参数统一按清单所在目录解析。
- **`SKILL.md:160` 让读者用 `memory_search` 取三条硬坑**：那三条是作者本机的记忆，换台机器就没有，与技能自称「跨机器可用」矛盾。改成正文内联（体积上限按字节 `209715200` B / OCR 缓存路径 `%DSH_HOME%\storages\pdf-reader\<sha256 前 16 位>\ocr\pNNN.json` / 写完必须 `insert into items_fts(items_fts) values('rebuild')`）。
- **两套验收标准打架**：`SKILL.md` §5 是「页数 / 书签 / 抽页目视 / 哈希」，`references/verify.md` 是「页数 / 顺序与字节 / 抽页目视」。统一成五条（页数 / 顺序与字节 / 书签 / 抽页目视 / 哈希），SKILL 写「细则在 verify.md，口径一致」，verify.md 补出 `## 3. 书签` 一节并顺延后面两节号。
- **`kb_ingest.py` 要求课程先存在而没写建课程这步**：脚本原来 `if not row: print("!! 课程不存在…"); return 1`，而 `_kb\app\kb.py` 并没有 `add-course` 子命令（建课程靠 `upsert_course` 的 `INSERT OR IGNORE`）。改成脚本自己 `insert or ignore into courses(name) values (?))` 再重查，打印「课程不存在，已自动建」。
- **结构与过时描述**：`SKILL.md` §4 的两段命令块挪进 `references/pdf.md` 第五节（原那里还写着已废的 `_kb\app\add_book.py` / `add_batch3.py` / `export_md.py`，一并换成 `scripts\kb_ingest.py` / `kb_to_md.py` 的完整命令），§4 只留三条目标表 + 一句指向；§9 目录从 2 个脚本补全到全部 10 个，并补「相对路径按清单目录解析」「首次运行自动建空清单」两条说明；`pitfalls.md` 的 `Remove-Item` 那条按 2026-11-21 复测改正（工作区内 / 工作区外 / 技能目录三处都不再被拦）。
- 回归：`append_batch.py` 三态实测通过、`kb_ingest.py` 改后语法与主流程未动（`py_compile` 通过）；`SKILL.md` 250 行 / 9914 字符（原 280 行 / 11127 字符），5 篇 references 与 10 个脚本引用零悬空、正文绝对路径 0 处。
