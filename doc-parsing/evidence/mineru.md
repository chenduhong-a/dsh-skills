# MinerU 版本与修复史（证据）

> 数据截止 **2026-11-26**。这里是「当时为什么这么改」的复现记录，判据在 `references/pdf.md` §1.1–§1.3，数字在 `evidence/mineru-measurements.md`。行号、commit 号是当时的代码位置，升级后会漂移，按语义找。

## 版本现状

- 本机 **4.2.3**，venv `$TOOLS_DIR\mineru4-venv`（`Scripts\mineru.exe` / `python.exe`）。
- `dsh-doc-parser` **0.3.15**（profile 里 `link:` 到 `$TOOLS_DIR\dsh-doc-parser`）。0.3.7 起按 4.x 的 `/v1/file_parse` 走，不再拼 3.x 的 CLI 参数。
- 旧 3.x 的 venv（6.6 GB）与 `.cache\modelscope` 的旧模型（1180.2 MB）已不被代码引用，2026-11-25 已删除；现在只有一条本地通道。

## 4.1.7 → 4.2.3：本地通道从「只剩 flash」到全档可用

**4.1.7 的症状**：本地只剩 `--tier flash`（只出文字，公式/图/表全是 `![Formula block](doc:…/block:N)` 空占位符），`standard/advanced` 报错：

```
Local parse-server is disabled. Use --tier flash or --remote.
```

代码位置 `mineru\doclib\services\parse_execution_svc.py:385`。4.x 的 `parse_server.local.mode` 有三值：`disabled`（默认）/ `managed`（MinerU 自己拉服务）/ `self_hosted`（你自己起，URL 填 `parse_server.local.self_hosted_url`）。

**4.2.3 的验证（2026-11-25，本机 RTX 5070 Ti + DirectML）**：

- `mineru-models-download --tier basic --small-backend onnx --source modelscope` 下 13 文件 / 839.3 MB 到 `%USERPROFILE%\.mineru`；
- 49 页物理论文 `tier=basic` 出 **90 个 equation 块（`content` 就是 LaTeX）+ 91 张 jpg**，无空占位符。
- 结论：「4.x 只能 flash」这条已不适用，别再照着挡升级。

**standard 档的模型**：`MinerU2.5-Pro-2605-1.2B` VLM（GGUF，531 MB 主模型 + 709 MB mmproj），`mineru-kit models download --tier standard` 下到同一目录，`models show` 显示 `MinerU2.5-Pro-2605-1.2B-GGUF: 就绪`。

## 0.3.9：按缺陷测试报告修五处

报告在 `$WORK_DIR\handover\bugtest-autotier.md`（共 7 条问题）。前三条是「figure-only 页拿不到 advanced 补跑」，后两条是「重复请求与重复记录」：

1. **`chart` 是独立块类型**：候选白名单原先只有 image/figure，且 standard 下 chart 空 content 被 `continue` 丢块 → 整页 0 块 → 请求直接报「没能解析」，p193/p222 这类纯图表页永远补不到 advanced（而 advanced 明明有 227/330 字的表格）。改为 chart 单独成支、空 content 给 `[chart — …]` 占位，`byPage` 为空时返回空记录而不是 `null`。
2. **替换判据从「页文本长度」改成「真文字长度」**：占位符与 VLM 图片描述不算，否则 advanced 多出一串 `Simple diagram of concentric circles…` 就会被当成升级（实测 p20 真文字 0→0 却被替换，页文本灌进 964 字符英文描述）。
3. **候选判定从「全是 image/figure」改成「没有真文字」**：页码/页眉/页脚不算文字，零块页也算候选。
4. **空页重试跳过 `null`**：已失败过的页不再请求一次（实测 4 页散页跑出 12 次 121 MB 上传、28 秒）。
5. **`failed` 按页去重**：同一页曾在「逐页重试失败」与「空页重试」各记一条，P5 实测 p193/p222 各有两条。

**未修**：缓存命中绕过自动分档、缓存键不含 tier（P3）；已先把 `tier` 写进缓存记录备查。

## 0.3.10：tier 在缓存里被覆盖

`doc_ocr` 主流程会在 `main.js:1466` 重建一条缓存记录，那里原先只透传 `via`，`tier` 得单独透传——表现是走自动分档后 `p<页码>.json` 里 `tier` 为空，查不出「这页是 advanced 补的」。已补（提交 `030399f`）。

重启后真跑 `doc_ocr` 验证：p193 出 227 字表格、p222 出三个表格共 330 字加一个 figure 块——**这两页在 standard 下都是空 chart 块（0 字），拿到的只能是 advanced 的结果**，说明自动分档在真实 `doc_ocr` 路径上跑通了。

## 0.3.11–0.3.15：全量缺陷测试后的五轮修复

四个并行子代理分片测（pdf / ocr / office / config），共 60 条；报告在 `$WORK_DIR\handover\bugtest-{pdf,ocr,office,config}.md`。

- **0.3.11（使用者最该记住的一条）**：`withImages=true` 时块文本变成 `![alt](path)` 图片链接，匹配不上 `[figure …]` / `[chart …]` 占位符正则，**纯图页因此被判成「有真文字」、拿不到 advanced 补跑**——表现是「开了 `withImages` 表格整页丢、不带图反而有表」；反向 `realTextOf` 又不跳过 `image` 块，会把 VLM 的英文图注当成升级依据灌进页文本（p20 从 842 字涨到 1887 字）。修后带不带 `withImages` 结果一致。
  - 同版还修了 **`doc_tables` 只认 `type === 'table'`**：4.x 在 standard 下把表格页认成 `chart` 块、把扫描页认成 `Text` 块，内容本身是标准 Markdown 表却被判成 `no table found`；判据改成「块文本里有没有 Markdown 表」（`b.type === 'table' || MD_TABLE_RE.test(text)`）。
- **0.3.12**：`mineru-mode.txt` / `mineru-tier.txt` **fail-closed**——文件存在但值不认识（含空文件）直接报错、不再回落环境变量。理由见 `references/pdf.md` §1.3：`mineru-mode.txt` 是隐私开关，回落就可能把 PDF 传上 mineru.net。
- **0.3.15**：补了 mode 的**作用域**——它只在真要决定走本地还是在线时读，有文本层的 PDF 根本不进这条路径（`doc_text` / `doc_tables` 的文本层启发式走 PDFium）。
- **0.3.4**：删掉 WMF 抽图死代码（`mathtype.js` 145 行），公式改走「LibreOffice 转 PDF + OCR」（`references/office.md` §3.3）。

## 4.x 的 CLI 兜底为什么不能用

`lib/ocr_mineru.py` 还是 3.x 的 `mineru --tier` 写法，4.x 下会给出看似成功的结果。插件里加了闸门——检测到 venv 里有 `mineru-kit.exe` 就抛错而不是给假结果；闸门必须放在 HTTP 通道「试过并失败」之后（放前面会把本可以走通的通道直接堵死，2026-11-25 踩过）。

## 环境变量的坑（为什么改读文件）

Windows 改用户级环境变量只写注册表、**不刷新已运行的 explorer**，宿主继承的是 explorer 启动那一刻的快照。2026-11-25 23:15 把 mode 改成 `local`、23:19 重启宿主，进程里读到的仍是 `online`。所以 0.3.7 起改读 `$TOOLS_DIR\dsh-doc-parser\mineru-mode.txt`（每次调用重读）。判真跑的唯一可靠证据是页缓存 `p%03d.json` 的 `via` 字段（在线写 `online`，本地为空），**不是页头 `(ocr mineru)`**。

## 4.x 端到端验通

2026-11-25 23:37，插件内 `doc_ocr` 对同一份 49 页 PDF 跑 `pages=1-2`（`force:true`）：缓存 `via` 为空（此前走在线时写的是 `via=online`），两页 8+6 块含 `Equation` 与 `Page-Number`（在线通道只给 `Text, Formula`），LaTeX 完整。
