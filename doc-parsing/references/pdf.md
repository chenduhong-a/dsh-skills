# PDF 与扫描件篇

> 本文件是 `doc-parsing` 复合技能的一篇。分诊与选篇见上级 `SKILL.md`；Office 文件（docx / pptx / xlsx）见同目录 `office.md`。
## 1. 通道选择

七个工具里与 PDF 相关的六个：`doc_info` / `doc_text` / `doc_render` / `doc_ocr` / `doc_tables` / `doc_parse`（`doc_formulas` 只解 OOXML，PDF 用不上，见 §4.1）。

| 要什么 | 用什么 | 注意 |
|---|---|---|
| 结构与页数 | `doc_info` | `probeLimit` 控制探几页，先看扫描页占比再决定下游 |
| 数字版正文 | `doc_text` | `pages` 支持 `1-3,5`；要坐标加 `withPosition` |
| 页图 | `doc_render` | `scale` 默认 2.5，看清公式再调 |
| 扫描页 OCR | `doc_ocr` | `engine` 只有 `mineru` 一个合法值（Indra 兜底 2026-11-18 移除，失败直接报错）；`force` 才重跑选中页；`prefetch` 只是后台排队（§2.2） |
| 表格 | `doc_tables` | `engine=auto` 先文本层启发式，整页无表才退 MinerU；`engine=mineru` 强制。**扫描页要整篇 Markdown 就用 `doc_parse`；只要表格用 `doc_tables engine=mineru`；两者都拿到时以 `doc_tables` 的列结构为准**（它保留行列，Markdown 的 HTML 表是纯文本） |
| 整篇 Markdown | `doc_parse` | 默认给图占位符，`withImages` 才落图 |

**表格判定过严的代价**：为保证「双栏正文不被当表格」把 `lowConfidence` 并进 thin 判定后，58 页纯文字文档 **58/58 全送 MinerU**（首调 24 页 GPU ≈43 秒，其余报 `(skipped: MinerU page cap 24 reached)`）。根因是 `lowConfidence` 的语义为 `rows.some(r => r.cells.length !== maxCols)`——任何一行格数不齐即为真，考题/诗歌/目录几乎必中；修法 `(lowConfidence && maxCols >= 4)`。看到「整本都在送 MinerU」先怀疑判定过宽，别急着加机器。

### 1.1 MinerU 版本：4.2.3 可用（4.1.7 的坑已修）

**症状**：想升 4.x 拿更好的公式；或在本地跑 `standard`/`advanced` 直接报错。

**判据（4.1.7 时代的历史坑，2026-11-25 已被 4.2.3 修掉）**：4.1.7 本地只剩 `--tier flash`（只出文字，公式/图/表全是 `![Formula block](doc:…/block:N)` 空占位符），`standard/advanced` 报 `Local parse-server is disabled. Use --tier flash or --remote.`（`mineru\doclib\services\parse_execution_svc.py:385`）。4.x 的 `parse_server.local.mode` 有三值：`disabled`（默认）/ `managed`（MinerU 自己拉）/ `self_hosted`（你起，URL 填 `parse_server.local.self_hosted_url`）。

**4.2.3 的实测（2026-11-25，本机 RTX 5070 Ti + DirectML）**：`mineru-models-download --tier basic --small-backend onnx --source modelscope` 下 13 文件 / 839.3 MB 到 `C:\Users\ZQY\.mineru`；`tier=basic` 对 49 页物理论文出 **90 个 equation 块（`content` 就是 LaTeX）+ 91 张 jpg**，没有空占位符——**「4.x 只能 flash」这条已不适用，别再照着挡升级**。省略 `tier` 时服务端按 `standard→basic→flash→advanced` 自动选；显式给不支持的档会被拒。

**版本判定别信 `pip index` 或更新面板，用 venv 里的 exe 跑版本 + 实跑一页看有没有 LaTeX 段落**：`& "$MINERU_VENV" -m mineru --version`，或直接 `& "C:\deepseek\tools\mineru4-venv\Scripts\mineru.exe" --version`（venv 路径见附录）。

**处置**：已升到 **4.2.3**（`C:\deepseek\tools\mineru4-venv`），`dsh-doc-parser` 0.3.7 起按 4.x 的 `/v1/file_parse` 走。旧 venv `mineru3-test`（6.6 GB）与 `.cache\modelscope` 的旧模型（1180.2 MB）已不被代码引用，可删。历史对照：3.4.5 曾实测 kittel 3 页 77 秒（**含模型加载与冷启动**）、热态单页 1.2–7 秒、8 个公式块全 LaTeX——两个数字不是同一口径，别拿 77÷3 当每页成本。

### 1.2 本地直调 HTTP API：4.x 是两个进程 + 一个 zip

**症状**：CLI 一页 10–12 秒，批量太慢；或拿到的 `content_list` 是空的、公式只剩编号。

**判据（4.x）**：`mineru-api.exe` 默认 **18000**，但它只有**异步** `/v1/tasks`；同步单文件口在另一个进程 `mineru-kit file-parse-server --api-url http://127.0.0.1:18000 --port 18001`，对外 `POST /v1/file_parse`。四个要点：①multipart 只认**单个** `file`（不是 `files`）；②`tier`（flash/basic/standard/advanced，省略则服务端按 `standard→basic→flash→advanced` 自动选）、`ocr_mode`（auto/txt/ocr）、`output_formats`（数组，`default` 给 zip）、`page_range`（**1-based 字符串**，如 `1-3`）；③响应是 **200 + 二进制 zip**（`application/zip`；202 才是 `StatusResponse`，带 status_url 要轮询）；④zip 里是 `structured_content.json`（`pages[].blocks[]`）+ `images/` + `markdown.md`，block 统一 `content` + `image_source`（`images/page_<n>_equation_<k>.jpg`，**不是** 3.x 那种 base64 data URI），`page_idx` 从 0 起算所以 `pnum = lo + page_idx`。解压用 `tar -xf`（Windows 自带 bsdtar 能解 zip，实测 exit 0）。实测：49 页物理论文 `tier=basic` 首轮 82.6 秒、3 页热态 2.6–3.9 秒。

**处置**：文件 >120 MB、页跨度 >40、服务不通 → `mineruHttpPages()` 返回 null，上游按「这段没解析出来」处理；**4.x 的 CLI 兜底尚未按 4.x 重写**（`lib/ocr_mineru.py` 还是 3.x 的 `mineru --tier` 写法），插件里加了闸门——检测到 venv 里有 `mineru-kit.exe` 就抛「同步通道（/v1/file_parse）没能解析这段页码，CLI 兜底尚未按 4.x 重写」而不是给假结果。

### 1.3 在线通道 mineru.net：四步，别自己猜

**症状**：本地 GPU 排队或太慢，想换在线；或直接调 API 报 403。

**判据**：`MINERU_MODE` 两挡（`online` / `local`）。**未设时的实际行为**（`main.js:442-446`）：本地 venv 在就走本地；venv 不在且有 token 才走在线；`local` 强制本地、`online` 强制在线。想知道这次会不会把教材传上去，先看这个变量与 venv 是否存在。`/api/v4` 四步：① `POST /file-urls/batch`（`{files:[{name,data_id}], model_version:"vlm"}`）拿 `batch_id` + `file_urls[]`；② `PUT file_url`（签名 URL，不带 token）传 PDF；③ 轮询 `GET /extract-results/batch/{batch_id}` 看 `state`（`waiting-file→pending→running→converting→done|failed`）；④ `full_zip_url` 下 zip，内含 `*_content_list.json` / `layout.json` / `full.md`。

**处置**：**PUT 上传不能带 Content-Type**——OSS 预签名把 header 算进签名，带了就 `403 SignatureDoesNotMatch`。token 存 `C:\deepseek\tools\.mineru-token`，有效期 90 天，额度 5000 文件/天。实测 0.11 MB / 3 页群论讲义：上传到 done 共 11 秒，zip 0.24 MB、content_list 12 块，公式 LaTeX 与中文都正确。
- **token 归属别只看前缀**：MinerU 控制台签发的 token 格式不统一（本机 2026-11-21 遇到过不带 `sk-` 的），按 OpenAI 习惯判「不是官方的」会误判；判据＝最小 `/file_parse` 请求或控制台对照，不是前缀。

### 1.4 兜底引擎 Indra 已移除（2026-11-18）

**现状**：`doc_ocr` 的 `engine` 只剩 `mineru` 一个合法值。Indra 连同插件自带的 `ocr-venv`（362.5 MB）一起摘除，MinerU 失败现在**直接报错**——不再静默降级成纯文本。插件体积 432 MB → 70 MB。

**历史判据（留作选型参考，别当能力用）**：纯文字 10 页中文教材平均 508 ms/页（0.34–0.69s），RapidOCR 同页 6143 ms——快约 12 倍，质量持平、公式页一样乱；模型 1M 参数、纯 CPU、首下 76 MB；`indra_ocr` 对中文路径有 bug，PNG 走 ASCII 路径。

**要纯文字怎么办**：`doc_text` 读文本层（0.3 秒）就够了；扫描页仍走 MinerU，公式与表格才有质量。

### 1.5 不要走 tesseract.js；onnxruntime 那条「必须钉旧版」已作废

**症状**：装 `tesseract.js` 7 想省 Python；或 `import onnxruntime` 零输出直接 `0xC0000005`。

**判据**：tesseract.js 7 在 Node 24 不可用（虚拟 FS 读不到语言包）——**别再换 OCR 引擎**：Indra 与随包的 RapidOCR 已于 2026-11-18 一起移除（§1.4），OCR 侧现在只有 MinerU；要纯文字先用 `doc_text` 读文本层。「必须 pin 1.19.2」的真因是**系统 VC 运行时被旧程序覆盖**——System32 的 `vcruntime140.dll`/`msvcp140.dll` 停在 14.00（VS2017），注册表已装 14.51；`VC_redist.x64.exe /repair` 换掉后 1.31.1 可正常 import。

**处置**：`/repair` 到 14.51（退出码 3010＝成功待重启），旧 pin 结论删除。判据：import 就崩且与设备无关 → 查系统 DLL；只在 GPU 崩且无栈 → 换库版本。

### 1.6 别拿「单页冷启动」当常态

单页冷启动 20 秒级（热态单页 1.2–7 秒，见 §1.1）。批量扫描件走 Windows OCR 或 MinerU 整批，插件只做单页/精修——不要一页一页调，那是在给冷启动交税。

### 1.7 扫描件要整篇 Markdown 怎么走

分诊表把扫描件指给 `doc_ocr`、把 Markdown 指给 `doc_parse`，两行不交叉——这是本手册以前最大的缺口。实际是两条路：

1. **首选 `doc_parse`**：它走 MinerU 通道，吃无文字层 PDF，直接给整篇 Markdown（LaTeX 公式 + HTML 表格；图默认占位，`withImages` 才落盘，见 §2.4）。≤120 MB / ≤40 页是本机实测的舒适区，超了不会立刻报错、但会变慢或撞上 MinerU 单批 24 页 cap，按 20–30 页一批拆开跑更稳。
2. **不上传（大文件/涉密/服务不通）就 `doc_ocr` 按页取**，再把页级 Markdown 按页码顺序拼起来——**拼接后必须重验**：跨页表、跨页公式会被切断（验收第 3 条），页码基准按 §3.5 标。

## 2. 验真：怎么确认真的跑了

### 2.1 force 传了，结果还是旧的

**症状**：加了 `force=true`，页缓存 mtime 变了，内容却没换。

**判据**：force 必须穿过调用链每一层：`doc_ocr` → `mineruBatch(abs, nums, outDir, {withImages, force})` → `mineruOnlineRun`（内部清 marker）→ `mineruParseFile`。任一环没传，就会出现「页缓存重写了、zip 照旧复用」。**判据是结果包的 `batchId`/`submittedAt`，不是页缓存 mtime**（实测 `446757a3` → `582b025a` 才算真重传）。**注意这两个字段只有 `doc_parse` 的输出带**（头部 `[batch … @ …]`，`main.js:1397`）；`doc_ocr` 与 `doc_tables` 不返回，用它们时按下节证据②③判。

**处置**：插件侧修法＝force 时既绕过缓存判断、又清掉 job marker；**使用者这一侧**只需重跑后核对 `batchId`/`submittedAt` 变了，别只看页缓存文件被重写。

### 2.2 分不清「缓存命中」还是「本次真跑」

**症状**：怀疑结果来自旧缓存；或去查缓存文件查不到。

**判据**：页文件名是 `p%03d.json`（`p001` / `p041`），路径 `$DSH_HOME\storages\pdf-reader\<hash16>\ocr\`——查 `p41.json` 会查不到。页头的 `(ocr mineru)` 是**引擎名**，不是置信度，也**不区分缓存与真跑**（`main.js:1206` 实测：MinerU 不返回 confidence，老版本那个恒为 `95%` 的数字是硬编码的假值）。要判真跑只能看下面的证据①与③。

**处置**：597 页固体理论教材落在 `88b7c5a356fe3123`，已全量缓存；插件改名不改缓存目录。
- **两条「真跑过」的证据，优先级从高到低**：①结果包 `batchId`/`submittedAt`（最硬，重传才会变；**只有 `doc_parse` 返它**）；②页文件 `p%03d.json` 的 mtime（最弱，force 也可能只重写文件）。走 `doc_ocr`/`doc_tables` 时只有②可用，所以验真退一步：**内容是否变了**（抽一页比对旧文本），而不是看文件动没动。原来那条「看页头 `(ocr 95%)` 还是 `(ocr mineru)`」的判据已作废——见 §2.2 判据段。
- **测吞吐别信 prefetch**：`doc_ocr` 的 `prefetch` 只是把页排进后台队列，返回「已排队」就算完成，拿它计时必然得到假的 0 秒——它只负责排队，不负责跑完。要测吞吐就跑 CLI 或直调 API，等真实产物落盘再除页数。

### 2.3 「验证通过」其实是循环论证

**症状**：拿两条路径互证，结果一致就宣布修好了。

**判据**：同一工具的另一条路径不能当基准——两条路可能一起错。真实案例：按「PDF 页号通常 1-based」给 MinerU 传 `start_page_id = lo`，整体偏一页，而内容完整、LaTeX 正常、页头还写着请求的页号、**不报任何错**；我用「直调结果 == CLI 缓存逐字一致」判定修复成功，但 CLI 那条路同样偏一页。

**处置**：基准必须独立于被测路径——渲染 PDF 原页看印刷页码、拿整本产出逐页对内容、相邻双页对照、别的工具产出的库。**偏移会污染缓存**——错内容写进 `p306.json` 之后所有查询都拿错的，修完要清掉对应缓存再重跑；另：别人说「已修好」时自己要有一次一手验证，别拿他的断言当基准。事实：MinerU 的 CLI `-s`/`-e` 与 API 的 `start_page_id`/`end_page_id` **都是 0-based**（`mineru --help` 原文 "beginning from 0"），内部调用要传 `页码-1`。

### 2.4 图「有」但打不开

**症状**：Markdown 里写着 `![](images/x.jpg)`，打开是空目录。

**判据**：`figure 8` 只是 content_list 计数，不代表文件落盘。`doc_parse` 默认把图改写成 `[figure: … (not extracted; pass withImages=true)]`；开了 `withImages` 才落 `<cache>/doc/images/` 并把链接换绝对路径。

**处置**：凡输出路径，落盘校验一次再交。**缓存键含 withImages**——先无图后有图会重跑，这是正常行为，不是缓存坏了。

### 2.5 CLI 跑完磁盘多了几百 MB

**判据**：Node `spawn` 不设 cwd 时子进程继承宿主当前目录，MinerU 会在 CWD 下建 `output/<uuid>/` 写整本 PDF 副本（本次 194.9 MB 无人清理）。

**处置**：固定到 `os.tmpdir()`；跑完看一眼 output 目录再收工。

## 3. PDF 结构

### 3.1 页数对不上

**症状**：解析出的页数比阅读器多一页。

**判据**：数 `/Type /Page` 会把残留孤儿对象算进去（本次 179 实为 178）。

**处置**：解析页树取 `/Count`。旧 `.ppt` 走 PowerPoint COM 打开读 `Slides.Count`（本机 Office16 可用），不必先找 LibreOffice。

### 3.2 无文字层，但要页图

**判据**：`/Font` 为 0；文本提取无解。

**处置**：`DCTDecode` 流本身就是完整 JPEG——从原始字节按 stream/endstream 抠出即得页图，Pillow 直接可读，不需要 PDF 库。

### 3.3 扫描件渲出来是白页

**判据**：pdfjs 缺 CCITT/JBIG2 解码器会渲成纯白；检测非白像素 <0.1%。

**处置**：改用 PDFium 重渲，不要拿白图去跑 OCR（会得到空文本，且不报错）。

### 3.4 扫描件朝向不确定

**判据**：凭直觉用 `ROTATE_270` 会得到 180° 倒图，白读一页。

**处置**：把原图 0/90/180/270 四份缩略图拼成 2×2 看一眼即可定准。

### 3.5 页码基准：三套页序一次对齐

同一份 PDF 里可能并存三套页号，混用会让结论指向错页：

| 页序 | 从哪来 | 注意 |
|---|---|---|
| PDF 物理页 | 阅读器页框、`doc_render`/`doc_text` 的 `pages` | 工具链内部计数；MinerU 的 `start_page_id` 是 0-based（§2.3） |
| 印刷页码 | 书页角标 | 常从物理页偏移 ±N，封面与前言常常没标号 |
| 课件标号 | PPT 幻灯片号 | 一份 PDF 常混排多份课件，标号会从头再来 |

做法：抽首、中、末三页，同时记「物理页 / 印刷页 / 标号」，三点定偏移；交付时统一写「PDF 第 N 页（＝印刷 pM）」。

**用户口述页码时默认按哪套**：按他看的那份阅读器的页框（通常＝物理页）取，取完在交付里回写一句「我按 PDF 物理页算的第 12 页＝印刷 p10」，让他一眼能对。别默认印刷页码。基准没对齐就继续取内容，后面对页码会全部错位（停止条件第 3 条）。

## 4. 公式与图片

### 4.1 PDF 里的公式

**判据**：MinerU 在线 vlm 能出 LaTeX；本地 3.4.5 pipeline 也行（kittel 8 个公式块全 LaTeX）。若 OCR 后公式只剩 `\tag{}` 编号，是 formula 开关没开，不是扫描质量问题。

**处置**：**PDF 不用 `doc_formulas`**——它只解 OOXML（pptx/docx）里的 OLE 与 WMF/EMF，PDF 里没有这些对象；PDF 的公式走两条：`doc_ocr`（MinerU 出 LaTeX）或 `doc_render` 出页图再视觉读。PPT 类文件里的公式见 `references/office.md` §3。

### 4.2 图的落盘与路径

**判据**：`withImages` 才落图（§2.4）；中文路径在 OCR 链路会乱码。

**处置**：中文路径先复制成 ASCII 或渲 PNG；交付前用文件系统确认图真的存在，再写进回答。

## 3.6 四个实测坑

- **MinerU 批量任务的中间产物留在 `output\<uuid>\` 不回收**：一次 274 页的任务留几百 MB，跑十次就是几个 GB。清理只删不在用的 uuid 目录，别动 `_cache`。
- **OpenAPI 里写 `default: true` 不等于实际默认开**：`formula_enable` / `table_enable` 文档标 default true，实际请求不带就是 false。要么显式传，要么先跑一页看输出里有没有 `$$` 与 `<table>`。
- **并发上限不等于并行度**：服务端 `concurrency` 写着 8，不代表开 8 路更快——实测 3 路并发比串行还慢（上传排队 + 单实例串行解析）。路数按「服务端实例数」定，不按上限。
- **同一工具多条路径，快慢差在「绕几层进程」**：同一批页实测 CLI 冷启动 50.9 秒 / CLI 热启动 10–12 秒 / 直调 HTTP 每次新进程 7.4 秒 / 直调 HTTP 常驻 3.35 秒。先问「这次是哪种」，再谈优化。

## 验收：什么时候算解析对了

**不比「跑完了没有」，比「内容对不对」**——OCR 与转换都不报错但结果是错的，是这个领域最常见的失败。

1. **页数对得上源文件**：`doc_info` 的页数与渲染出的页图数一致；少页、多页、空白页都要当场查。
2. **抽 2–3 行原文逐字比对**：挑正文中段（避开标题区与页边），与源 PDF 肉眼对照——错字允许，**改内容、漏段、串页不可接受**。
3. **表格行列数与源一致**：列数对不上通常是合并单元格或跨页表；跨页表要拼起来再看一次。
4. **公式与图片数量与页面对应**：公式页该有公式、图页该有图；图片给了路径就打开一张确认不是 0 字节。
5. **说清这是哪一次跑的结果**：报缓存目录里的 `<hash16>`（`$DSH_HOME\storages\pdf-reader\<hash16>\ocr\`，`doc_info` 或缓存路径里就有）与本次选页数、`savedPages`/`freshPages`，证据与优先级见 §2.2，不能只说「验证通过」。
6. **结论里带页码基准**：写「第 N 页」时注明是 PDF 页序还是印刷页序（三套页序怎么对齐见 §3.5），否则别人按你说的页码找不到。**指标变好不等于内容变对**：全库重抽后汉字率、LaTeX 命中率都上去了，仍要抽 3–5 页连公式和表格一起看——指标只证明「更像文字了」，不证明「内容对了」。
7. **判质量不能只数乱码符**：旧式 OCR 可能一个 U+FFFD 都没有，汉字率却只有 7.5%。三条判据一起看——汉字占比（正文段应 >60%）、LaTeX 命中率（有公式的书该出现 `$$`）、抽一段读得懂读不懂；只看「有没有乱码」，会把「整页读成合法汉字但全是错的」放过去。
8. **「空页」要说清是哪个口径**：白页（渲染后全白）/ 无文字层 / OCR 后无内容，三个数量不一样，报告时写明按哪个口径数的，否则两个人像在互相纠正。

做不到第 2 条就别交付——**「跑完了」不等于「解析对了」**。

## 已知缺口（2026-11-21 审计补，没实测的不写命令）

- **`doc_ocr` 的 `pages`**：写法同 `doc_text`（`1-3` 或 `1-3,5`，缺省全部页，`main.js:951`）；**单次页数上限没实测**，批量时按 20–30 页一批，报错或明显变慢再减半。
- ~~`doc_tables` 的输出格式未知~~（2026-11-22 读源码补上）：两条路混排——**MinerU 路线给 HTML 表格**（页头 `MinerU` 或 `MinerU fallback (no text layer)`，相邻页首行相同会标 `[continues table from pN]`），**文本层启发式路线给 TSV**（页头 `N cols`，可能带 `low confidence`）。另有三种「没表」要分开读：`skipped: MinerU page cap N reached`（该页没进 MinerU，用 `pages` 收窄或调大 `maxMineruPages`，默认 24）、`MinerU unavailable`（服务挂了，与「确实没表」不同）、`no table found`（真没有）。按页指定用 `pages`，写法同 `doc_text`（见上一条）。
- **60 页整本的端到端耗时**：现有三组数字口径不同（kittel 3 页 77 秒含冷启动、热态单页 1.2–7 秒、32 页 40.8 秒），推不出总时长；要估就热态测一页再乘页数。
- **跨页表拼接**：只有「拼起来再看一次」的原则，没有可执行做法。
- **本地 MinerU 服务的前置条件**（`MINERU_API_URL`、模型缺失、显存不足、端口占用）没有排错段；服务不通时按 §1.2 退回 CLI。

## 什么时候停（停止条件）

- **同一通道连试两次都失败** → 换通道（文本层失败转 OCR、OCR 失败转渲染读图），别在同一条路上试第三次。
- **缓存命中的结果看着不对** → 先 `force` 重跑一次确认是缓存问题；还是一样就判定源文件问题，不要反复刷缓存。
- **页码基准对不上** → 停下来先对齐基准（PDF 物理页 vs 印刷页码 vs 课件标号），基准没对齐就继续取内容，后面对页码会全部错位。
- **扫描页比例超过一半** → 直接整本走 OCR，不要逐页试文本层。
