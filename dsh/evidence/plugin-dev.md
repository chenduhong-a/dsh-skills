# DSH 插件开发：案例与实测证据

> **本文件是案例与实测证据，执行时不必读。** 动手写插件、改工具时读 `references/plugin-dev.md`；只有要追溯某条判据的来历、报错原文、耗时数字，或想知道「这条规矩是被哪次翻车逼出来的」，才翻这里。
>
> 组织方式：§0–§6 与 references 的节号一一对应。下面的报错、路径、字节数、毫秒数都是当时现场原文或实测值，未重新测量；涉及的插件（`doc_ocr`、`doc_formulas`、`pdf_ocr_page`、`dsh-doc-parser` 等）与版本按当时现场保留。引用旧结论先看日期——环境已变的部分（indra 引擎已移除、pwsh 已升 7.x）只作原理参考，不当作现状。

## §0 判据与入口

- **第三方插件审计的去处**：本技能「门控四层」+ 解包做六类 grep 人工审（`child_process`/`net`/`eval`/写盘 API/外连 URL/`process.env`）。2026-11-20 起 `vet-audit-protocol` 技能随 `@jieai/dsh-plugin-vet` 卸载一并消失，这条路只剩手工 grep。
- **R3 误报实测（2026-11-21，`dsh-cookie-guard 0.1.1`）**：`scan_plugin` 判 0 分 critical，命中项是 bin 入口里的 `process.exit`／`process.argv`／`process.env`；R3 针对「输入可驱动的动态求值/联网」，bin 入口读 argv/env 不构成风险，人工复核后放行。
- **原稿的一处断链**：「开工前四查」第 2 条原文写「见下面『接手别人的插件』」，但全文没有这一节。新 references 已改为指向 `references/ops.md` 的门控 + 六类 grep。
- **原稿的自我定位**：「读者是插件作者，不是运维。这里的每一条都对应一次实际翻车，处置顺序按『先救命、后优化』排。」这条决定了新版只留会翻车的点与处置顺序，功能总览、架构介绍一概不写。

## §1 工具定义契约

**症状原文**：宿主报 `unknown tool`；日志里没有异常；自己写的白盒 apply 测试全绿。

**判据原文**：`output: {schema, render}` 是 ToolDefinition 的必填项（内核里是 readonly output）。漏了它，该工具会被 register 的 try/catch **静默跳过**，宿主报 `unknown tool`，而白盒 apply 用假 `ctx` 不校验 output → 测试全绿，假绿。

**注册语义**：注册返回成功不等于工具可用：热重载不重新注册工具，改完必须重启才生效。原稿特别提醒「不要用热重载后的『工具在列表里』当通过」。

**字段编辑事故（原稿处置 2、3）**：

> 改 `parameters` 后用 `read` 复查整个对象。用 edit 插参数时最容易连带删掉相邻的 `output:` 与 `timeoutMs:`——一次只改一处、改完就读。
>
> 多个工具共享同一段字段时先找唯一锚点：`maxChars` 在两个工具里一字不差，直接 edit 报 `matched 2 times`；必须带上前一个参数一起匹配。

**处置 4**：改完重启宿主，再验工具面与最小用例。

## §2 缓存与 force

**症状 A**：传了 `force=true`，耗时没变（例如仍是 275 ms 就返回），结果还是旧的。

**判据**：force 必须同时做到三件事，缺一件即形同虚设——参与缓存判断、穿过调用链每一层、清掉旁路标记。

三个真实漏法：

1. **只改底层没改调用点**：`doc_ocr` 的 `force` 只改到底层 `mineruOnlineRun`，调用点 `mineruBatch` 那层没传 → 页缓存重写了，但 `online-task.json` 没清、旧 zip 照旧复用。
2. **复用逻辑仍按「缓存有内容就命中」**：`doc_ocr` 与 `doc_formulas` 都栽在这。修法＝force 时既绕过缓存判断，又清掉 job marker。
3. **只在一个分支加短路**：给 `pdf_ocr_page` 加 force 时只改了 pdfjs 分支 `if (!force && isRealTextLayer(t))`，漏了 PDFium 兜底分支 `if (isRealTextLayer(vt) && !textLayer.has(n))` → `force=true` 仍命中文本层、275 ms 返回，还把已有的 `engine:'mineru'` 记录改写成 `engine:'text'`、blocks 全丢。

**处置原文**：

1. grep 判定函数**本身**，不 grep「我找到的那一处」：`isRealTextLayer`、`textLayer.set`、`cacheFile` 写入点，把所有调用点列出来逐条核对。同一语义出现在几条分支，就检查几个地方。
2. 验收看会变的东西：结果包里的 `batchId`/`submittedAt` 变没变；只看文件 mtime 会误判成已修。
3. 这类漏改自审不可靠——我自己读第二遍看不出来，独立测试 agent 一跑就复现。必须有黑盒回归。

**症状 B**：换了参数仍命中旧结果，或每轮重跑覆盖。

**判据**：缓存键漏了影响输出的参数。

- 命中条件只看 `lang`/`engine`、不看 `withImages` → 「先跑无图、再要图」会静默命中旧记录。**凡改变输出的参数都必须在缓存键里**。
- 缓存判断写 `rec.engine === 'indra'`，而文本层缓存是 `engine=text` → 每轮重跑覆盖。修法：加 `|| rec.engine === 'text'`。（Indra 2026-11-18 已移除，案例仍说明「缓存键要查全所有引擎分支」。）

## §3 判定条件与解析器

**症状 A**：为防「X 被误判成 Y」而加严条件，结果正常文档全被送去跑重活。

**判据（加严三查，原文）**

1. **按「谁容易满足」审一遍语义**。`lowConfidence` 的语义是 `rows.some(r => r.cells.length !== maxCols)`——任何一行格数不齐即为真，考题、诗歌、目录几乎必中。把它并进 thin 判定后，58 页纯文字文档 **58/58 全送 MinerU**（首调 24 页 GPU ≈43 秒，其余报 `(skipped: MinerU page cap 24 reached)`）。
2. **加严后用真实语料 × 单页成本算总代价**（页数 × 秒），别只验一个样本「看起来对了」。
3. **两级门控分层**：便宜且高召回的信号留第一层，昂贵操作只在强信号触发。修法示例：`(lowConfidence && maxCols >= 4)`。

**症状 B**：用户说「跑 3 页」，实际跑了整本，且不报错。

**判据**：解析函数静默跳过非法输入，调用方又把空结果当「全部」。

- 实例：`parsePages('abc')` 返回空数组，调用方见空又退回「全部页」。
- 铁律：**语法错要抛错，只有范围越界才返回空**。

## §4 子进程、外部服务与免重启自测

**症状 A**：跑完外部程序，工作目录里多出几百 MB 副本。

**判据与处置**：Node 里 spawn 外部程序必须显式设 `cwd`——子进程默认继承宿主当前目录，MinerU 会在 CWD 下建 `output/<uuid>/` 写整本 PDF 副本（实测 **194.9 MB** 无人清理）。固定到 `os.tmpdir()` 才可控。

**症状 B**：给「每次调用冷启动几十秒」的外部服务接常驻通道，怕改坏。

**四条设计（MinerU 实例：单页 50.9 秒 → 9.6 秒）**

1. **两端都探活**：Node 侧 400ms TCP 决定要不要自动拉起，python 侧 500ms 决定要不要加 `--api-url`。探活只验端口，不验 HTTP 语义。
2. **不可用时传空串走原路径**：旧行为自动成为 fallback，天然「只慢不坏」。
3. **API 模式失败要换新输出目录重试**：否则半成品产物会被当结果读走。
4. **自动拉起加「每宿主进程只试一次」+ 环境变量开关**：避免反复 spawn 几十秒的重进程。

**症状 C**：改一行就要重启宿主，验证成本高。

**通道（按优先级，原文）**

1. **免重启自测**：node 里 `import lib/main.js` → `mod.apply({ tools: { register } })` 收集工具 → `tool.execute(args)`，绕开宿主验证的是真代码。
2. **白盒 import 插件用 `file:///C:/...`**：ESM 不接受 `C:\` 绝对路径，会抛 `ERR_UNSUPPORTED_ESM_URL_SCHEME`。
3. **用桌面版自带 Electron 当 node**：`$env:ELECTRON_RUN_AS_NODE=1` 后调 `C:\deepseek\官方\DeepSeek Harness.exe`（v24.21.0）。它是 GUI 子系统，pwsh 里 `&` 不等待也拿不到退出码，必须 `Start-Process -Wait -RedirectStandardOutput/-RedirectStandardError`。
4. **优先用真 node**：`C:\Users\ZQY\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe`（2026-11-13 起）。
5. `spawnSync('pwsh')` 静默 `exit null`、0.2 秒返回、stderr 为空——**只对 PowerShell 5.1 成立**（2026-11-13 起已装 pwsh 7.7.0，可直接用 `pwsh`），但仍建议 `process.env.PWSH || 'pwsh'` 留退路。

**症状 D**：一接第三方异步 API，字段写错只能看到插件层的模糊报错。

**处置（接之前先写探针）**：探针只跑最小链路（认证 → 提交 → 轮询 → 取结果），字段写错能立刻看到原始 HTTP 400/401；直接改插件则要重启宿主，还得在缓存与分页逻辑里倒推是哪一步错。探针保留成独立文件（如 `C:\deepseek\tools\mineru-online-probe.mjs`），既是验收工具也是接口文档。

**症状 E**：删测试目录报 EPERM。

**判据**：占用进程的 CWD 指向该目录，目录本身被锁（里面的文件却能删）。测试遗留的 node mock 服务、孤儿 python multiprocessing 子进程都会这样。`Stop-Process` 掉它们再 `fs.rmSync`。

## §5 工具输出的读者是模型

**判据**：每条输出都问一句「换个陌生人读，会不会被误导或白读」。

1. **别枚举本该压成区间的数据**。`scanned pages: 1, 2, 3, … 300` 逐页列出，一本 597 页的书每次调用白烧 1.5K token；写 `all 597 (597 page(s))` 或 `1-5, 9, 12-20`。
2. **别输出指向不存在文件的路径**。默认不导图时 markdown 里仍写 `![](images/fig-3.jpg)`，文件没落盘，读的人以为能打开、白找一圈。要么写清「not extracted; re-run with withImages=true」，要么干脆不写图片语法。
3. **路径必须落盘校验**。`figure 8` 只是 content_list 计数，`![](images/x.jpg)` 可能指向一个从没落盘的目录。同类坑已犯两次（pdf 插件、doc_parse）——凡是输出路径，落盘校验一次再交。
4. **数字必须有来源**。MinerU 不返回置信度却硬编码 `confidence: 95` 并打印「ocr 95%」，比没有更坏；记 `null`、显示引擎名。
5. **改完动版本号**。描述里早写 MinerU 3.4.5，`version` 却停在 0.1.0，将来分发或回滚认不出这批改动。

## §6 审读、自评与收尾

### 6.1 审「能用但慢」的代码：先找三类放大

1. **N 次重复整文件操作**：`for (n of nums) await ocrMineruPages(pdfAbs, [n])` 每页把整份 PDF 读进内存上传一次，10 页＝10 次上传。正确是两阶段：便宜启发式先筛，需重活的页一次批量跑完再按页归位。
2. **缓存键漏参数**：见第 2 节。
3. **编造的元数据**：见第 5 节。
4. 附带两个小点：探活加进程级短缓存（400 ms × 每页很贵）；同一阈值判断写两遍就该抽函数。

**审读顺序原文**：execute 的循环体（放大在这）→ 缓存命中条件（语义错在这）→ 输出数字有没有来源。

### 6.2 自评双线

- **一条黑盒、一条静态，并行**：派 teammate 跑黑盒的同时自己 grep 旧名、读参数表、查输出上限。「过时文案与废弃参数」这类问题黑盒测不到，但会误导模型。
- **派测试 agent 的任务书要给六样**：①源码路径与全部工具名；②两条测试通道（黑盒真调 + 白盒 `import lib/main.js` + 假 `ctx.tools.register` 收集后直接 `execute`，能注入坏参数）；③本机 node 绝对路径；④素材路径与「产物只许写某个目录」的写入范围（配 `team_task_create` 的 writeScopes）；⑤报告格式：BUG 编号/严重度/复现步骤/期望/实际/证据路径；⑥「发现严重问题先单独发消息，不用等全跑完」。
- **它的价值在「敢乱用」**：会构造空 PDF、坏 schema、force 连击、并发双路这些人类懒得试的输入。实测 17 分钟交回 12 个 BUG，其中 1 个是我审 1290 行没看出来的严重 bug（prefetch 结果被 IIFE 丢弃）。

### 6.3 用户说「全做」时的节奏

1. **先分段再动手**：按依赖排成性能/语义/能力三组，一组改完立刻 `node --check` + 实测，别一口气写 300 行再验。
2. **性能项先量基线再改**：先量出「140 MB 153 ms / 572 MB 408 ms」才敢说「省 0.4 秒」，改完再量热耗时（0 ms）。否则「优化」只是感觉。
3. **改 schema 最易误删相邻字段**：见第 1 节。
4. **多工具共享的改动先找唯一锚点**：见第 1 节。
5. **改完同步三处**：README、`插件说明.txt`、代码注释；注释讲「为什么这样改」，不是「改了什么」。

### 6.4 改名 / 合并后扫旧名

**症状**：工具改名了，读者（模型）还在找不存在的工具、翻旧缓存目录。

**范围六处**：工具名、源码路径、缓存目录、进度条接口路径、技能文档、记忆库里的事实条目。

**实例**：`dsh-pdf-enhanced` + `dsh-pptx-formula` 合并为 `dsh-doc-parser`，工具名全换（`pdf_*`→`doc_*`），但缓存目录仍沿用 `storages\pdf-reader\`。

**判据**：`grep -rn '旧名' 代码 技能 记忆库` 三处都要过一遍。

### 6.5 体检残留六类（照单过，原文）

1. **临时诊断日志**：调试时加的 `loadLog()`/`appendFileSync` 写盘，bug 修完没删。搜 `appendFileSync`、`writeFileSync` 与「临时/诊断/debug」注释，看有没有删除路径。
2. **空函数与死导出**：重构后留下的 `disposeOcr(){}` 空壳。数每个导出被 `main.js` import 的次数。
3. **README 与代码脱节**：最容易骗人，逐条核版本号与「默认/必须/不支持」。
4. **`package.json` description 停在早期设计**：写「纯本地 CPU」实际走 GPU。
5. **一次性调试脚本**散在根目录、硬编码别人机器路径：看是否被任何入口引用，没引用就归档并注明「import 已失效」。
6. **真别动**：venv、node_modules、lock 文件、仍在被引用的备用引擎通道。

### 6.6 脚本说「成功」不算数

- **删死代码后核行数**：第一次用 `lines.splice()` 删行，却忘了 `s = lines.join('\n')` 同步回字符串，写回的还是原内容，脚本还打印 `bytes 7973 -> 8503`。判据应是**行数 + 残留关键词双查**（`lines after` 232 没变就该警觉）。
- **改文档别在 PowerShell 里拼**：反引号是转义符，双引号字符串与 here-string（`@"..."@`）都中招，6 处替换只中 4 处。一律用 `write` 写临时 `.mjs` 再 `node` 执行，写完用 `Select-String` 或 node 复查命中数。
- **临时脚本的扩展名**：`.mjs` 按 ESM 解析，`require` 报 `not defined in ES module scope` → 改用 `.cjs`。
