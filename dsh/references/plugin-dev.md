---
name: dsh-plugin-dev
description: DSH 插件与工具的作者手册——工具定义契约、缓存与 force 的语义、解析器写法、免重启自测、输出给模型看的写作规则、收尾检查清单。写新插件、改别人的插件、给工具加参数或 force 时加载。执行只读本文件，案例与实测在 evidence/plugin-dev.md。不含装卸升级（见 references/ops.md）。
---

# DSH 插件作者手册（执行面）

> 读者是插件作者，不是运维。本文件只留「怎么做」与契约；每节第二行的指针指向该判据的翻车现场（`evidence/plugin-dev.md`，按节号查）。

## 判据

**什么时候翻**：新写 DSH 插件，或给已有插件加工具、加参数、加 `force`；改别人写的插件（含另一个工作区改过的共享插件）；现象是「工具注册了但调不到」「force 没反应」「输出骗人」「能用但慢得离谱」「改名后模型还在找旧工具」；要给插件做自测/回归，或给测试 agent 写任务书。

**不归这里管**：装/升/卸已装包、门控、版本真伪 → `references/ops.md`；环境体检 → `references/selfcheck.md`；审第三方插件能不能装 → 本技能「门控四层」+ 解包六类 grep 人工审（`child_process`/`net`/`eval`/写盘 API/外连 URL/`process.env`）。
   - **六类 grep 的可用正则**：①`child_process|spawnSync|spawn\(|execSync` ②`net|dgram` ③`eval\(|new Function` ④`writeFile|createWriteStream|unlink` ⑤`process.env` ⑥`"(pre|post)?install"`（`package.json` 的 scripts）；六类 0 命中却仍联网/写盘＝换了写法（base64、`Function` 拼接、原生 addon）。

**开工前四查（顺序固定）**

1. **读入口与工具表**：按 `package.json` 的 `main`/`exports` 取真实入口，不靠猜；列出每个工具的 `name`、`parameters`、`output`。
2. **判可装性/可改性**：`references/ops.md` 的门控 + 上面六类 grep。
3. **grep 语义锚点**：判定函数（`isRealTextLayer`、`textLayer.set`、`cacheFile` 写入点）的**全部**调用点先列全，再决定动哪。
4. **先备一条免重启自测通道**（第 4 节），否则改一行就要重启一次。
- **判「能不能改造」先比接口再比功能**：看它怎么发消息、挂事件、注入上下文（OpenViking 用 `createUserMessage` + `source.form`，meow 用 `form: "snapshot" | "notice"` + `sections`）；接口同构＝机制可搬，只比功能列表答不出挂载点。

## 1. 工具定义契约
依据见 evidence/plugin-dev.md 第 1 节。

### 1.0 最小可运行骨架（从真实插件抽出，去掉业务逻辑）

```js
// lib/main.js —— package.json 的 main/exports 指这里
export const inject = ['tools'];   // 要哪些宿主服务；名字必须在内核里真实存在（见 references/ops.md 1.3）

const TOOLS = [{
  name: 'my_tool',
  description: '给模型看的说明：什么时候用、参数含义、返回什么。',
  parameters: {
    type: 'object',
    properties: { path: { type: 'string', description: '绝对路径' } },
    required: ['path'],
  },
  output: { schema: { type: 'string' }, render: (_args, value) => text(value) },  // 必填，漏了会被静默跳过
  timeoutMs: 60000,
  async execute(args) { return '结果字符串'; },
}];

export function apply(ctx) {
  for (const tool of TOOLS) {
    try {
      tool.isConcurrencySafe ??= () => true;
      tool.presentCall ??= (args) => ({ card: 'generic', title: tool.name, kind: 'read', rawInput: args });
      ctx.tools.register(tool);
    } catch (err) {
      console.error(`[my-plugin] register ${tool.name} failed: ${err?.stack || err}`);
    }
  }
}

// render 的返回值是 ContentBlock 数组
function text(value) { return [{ type: 'text', text: String(value) }]; }
```

**三件事别省**：`inject` 里只写内核真有的服务；每个工具都必须有 `output.schema` 与 `output.render`；`register` 包在 try/catch 里时，catch 只打日志＝出错静默跳过（这正是「工具注册了但调不到」的来源），开发期最好让它抛。

- **必填**：工具在 `apply(ctx)` 里用 `ctx.tools.register(def)` 注册，`def` 写全 `name`/`description`/`parameters`，外加 `output: {schema, render}`——后者在内核里是 readonly 必填项。
- **红线**：漏 `output`，该工具会被 register 的 try/catch **静默跳过**，宿主报 `unknown tool`；而白盒 apply 用假 `ctx` 不校验 output → 测试全绿是假绿。
- **反推别人的 API 要读两份契约**：注册契约之外还有返回值契约——枚举值、错误码、字段可选性都在后者，只抄「怎么注册」再自己扩枚举会在边界值静默失败；判据＝能指出该 API 在源码里的定义位置与调用方实际用法，两点对上才算反推成功。
- **注册成功 ≠ 可用**：热重载不重新注册工具，改完必须重启宿主，再验工具面与最小用例。
- **改参数**：改完用 `read` 复查整个对象——edit 插参数最容易连带删掉相邻的 `output:` 与 `timeoutMs:`，一次只改一处、改完就读。
- **共享字段**：多工具里一字不差的同一段（两处 `maxChars`）直接 edit 报 `matched 2 times`，必须带上前一个参数匹配出唯一锚点。

### 1.1 工具没出现时，`fiberPhase=active` 不算成功

`register()` 校验失败会被插件 `apply` 里的 try/catch 吞掉（只 `console.error`，桌面版 stderr 不落盘，日志目录查不到），面板上看起来一切正常。排查按这个顺序，别一上来怀疑宿主没重启：

1. `profiles\<name>\package.json` 的 `dsh.profile.bundles` 里有没有这个包（`dsh.dependencies` 常为空，**不看它**）；
2. 插件的 `cordis.patch.yml` 插入写法是否与一个能用的插件同款；
3. `node_modules\<pkg>` 副本与源码逐文件 hash 比对（`file:` 安装是硬链接，改一边另一边可能没动静）；
4. `plugin_manager list_plugins` 里它的 `fiberPhase`；
5. `cordis_inspect_query` 的 host / `Tool/listTools` 搜工具名；
6. 同一接口的 `Service/listService` 看 `register` 契约；
7. 拿一个能用的插件 diff 工具对象的字段——缺 `output` / `timeoutMs` / `isConcurrencySafe` 这类，装配时就炸。

## 2. 缓存与 force
依据见 evidence/plugin-dev.md 第 2 节。

- **force 先在 `parameters` 里声明成 boolean（默认 `false`），再保证三件事**（缺一件即形同虚设）：①参与缓存判断；②穿过调用链每一层；③清掉旁路标记（job marker、旧产物、文本层记录）。
- **缓存键**：缓存是插件自己实现的（自己定键、自己判命中），漏了没人兜底——**凡改变输出的参数都必须在缓存键里**（漏 `withImages` 这类，先跑无图再要图会静默命中旧结果）；命中条件要把所有引擎分支列全——`engine === 'text'` 与旧 indra 分支是同一语义的两条路，只写一条就每轮重跑覆盖。
- **grep 范围**：grep 判定函数**本身**，不 grep「我找到的那一处」；同一语义出现在几条分支，就检查几个地方。
- **验收**：看会变的东西（结果包里的 `batchId`/`submittedAt` 变没变），只看文件 mtime 会误判成已修；这类漏改自审不可靠，必须有黑盒回归。

- **「改了没生效」先查代码路径可达，别怀疑宿主**：`if (!args.force && !probe.scanned) continue;` 这样一行前置过滤，会让后面新加的分支永远不执行——重启两次都白费。排查顺序：①日志确认模块加载了 → ②grep 前置过滤 / `return` / `continue`，确认目标分支在可达路径上 → ③再测行为。

### 2.1 代码改了行为没变，四查

按顺序排：

1. **是不是有多处赋值**：默认值写真值的地方可能不止一处（`argparse` 的 `default=`、配置镜像、文档示例），改一处其余照旧；
2. **模块是不是已经加载**：长驻进程里改源文件不生效，要重启宿主；
3. **是不是按哈希/时间缓存**：有些加载器按内容哈希缓存编译产物，源码变了但哈希没重算；
4. **`applied` 不等于就绪**：配置写进去了不等于已生效，看运行时的实际字段而不是配置文件。

## 3. 判定条件与解析器
依据见 evidence/plugin-dev.md 第 3 节。

- **加严三查**：①按「谁容易满足」审语义（`rows.some(r => r.cells.length !== maxCols)` 任何一行格数不齐即为真）；②用真实语料 × 单页成本算总代价（页数 × 秒），别只验一个样本「看起来对了」；③两级门控分层：便宜且高召回的信号留第一层，昂贵操作只在强信号触发（如 `lowConfidence && maxCols >= 4`）。
- **解析器铁律**：**语法错要抛错，只有范围越界才返回空**——解析函数静默跳过非法输入、调用方又把空结果当「全部」，就会「跑 3 页」变成跑整本且不报错。
- **兜底路径要比失败本身更响**：`except Exception: return []` 会把「依赖没装」变成「结果就是空」——本项目 `kb.py` 的向量检索因此静默返回空列表，6300 多条向量白建、没人发现。按异常类型分别给提示（缺依赖就把装的命令打出来）、每个进程只提示一次，别让兜底把故障吃成静默降级。

## 4. 子进程、外部服务与免重启自测
依据见 evidence/plugin-dev.md 第 4 节。

- **spawn 必须显式设 `cwd`**：子进程默认继承宿主当前目录，外部程序会在 CWD 下写整本 PDF 副本；固定到 `os.tmpdir()` 才可控。
- **常驻通道四条设计**：①两端都探活（Node 侧 400 ms TCP 决定要不要自动拉起，python 侧 500 ms 决定要不要加 `--api-url`；只验端口不验 HTTP 语义）；②不可用时传空串走原路径，旧行为天然成 fallback「只慢不坏」；③API 模式失败要换新输出目录重试，否则半成品产物会被当结果读走；④自动拉起加「每宿主进程只试一次」+ 环境变量开关。
- **免重启自测（按优先级）**：① node 里 `import lib/main.js` → `mod.apply({ tools: { register } })` 收集工具 → `tool.execute(args)`，绕开宿主验证真代码；②白盒 import 用 `file:///C:/...`（ESM 不接受 `C:\` 绝对路径，抛 `ERR_UNSUPPORTED_ESM_URL_SCHEME`）；③用桌面版自带 Electron 当 node：`$env:ELECTRON_RUN_AS_NODE=1` 后调 `C:\deepseek\官方\DeepSeek Harness.exe`，它是 GUI 子系统，pwsh 里 `&` 不等待也拿不到退出码，必须 `Start-Process -Wait -RedirectStandardOutput/-RedirectStandardError`；④优先真 node：`C:\Users\ZQY\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe`；⑤调 PowerShell 写 `process.env.PWSH || 'pwsh'`，别写死路径。
- **接第三方异步 API 先写探针**：探针只跑最小链路（认证 → 提交 → 轮询 → 取结果），字段写错能立刻看到原始 HTTP 400/401；探针保留成独立文件，既是验收工具也是接口文档。
- **删测试目录报 EPERM**：占用进程的 CWD 指向该目录（测试遗留的 node mock 服务、孤儿 python 子进程），目录本身被锁而里面的文件却能删；`Stop-Process` 掉它们再 `fs.rmSync`。

## 5. 工具输出的读者是模型
依据见 evidence/plugin-dev.md 第 5 节。每条输出都问一句「换个陌生人读，会不会被误导或白读」：

1. **别枚举本该压成区间的数据**：逐页列 300 页是白烧 token；写 `all 597 (597 page(s))` 或 `1-5, 9, 12-20`。
2. **别输出指向不存在文件的路径**：默认不导图就别写 `![](images/fig-3.jpg)`；要么写清「not extracted; re-run with withImages=true」，要么干脆不写图片语法。**凡是输出路径，落盘校验一次再交**。
3. **数字必须有来源**：引擎不返回置信度就别硬编码 `confidence: 95` 并打印「ocr 95%」；记 `null`、显示引擎名。
4. **改完动版本号**：描述里早写了新引擎版本、`version` 却停在 0.1.0，将来分发或回滚认不出这批改动。
5. **截断按语义单位切，不按字节**：超限时以「页/条/行」为单位切（如 `clampByPages`），每刀在结果里带 `omitted` 与续读游标；按字符硬截会把表格/代码块/JSON 截断，模型读到坏结构比少给更糟。

### 5.1 工具返回值必须无损 JSON

工具结果要能被 JSON 序列化且不丢字段：`undefined`、`NaN`、`BigInt`、循环引用都会让内核侧拿到的值是错的或整个调用失败。返回前过一遍 `JSON.parse(JSON.stringify(x))` 看有没有字段消失——`undefined` 的键在序列化时直接不存在，模型看到的就是「没这个字段」。

## 6. 审读、自评与收尾
依据见 evidence/plugin-dev.md 第 6 节。

### 6.1 审「能用但慢」：先找三类放大
- **N 次重复整文件操作**：`for (n of nums) await ocrMineruPages(pdfAbs, [n])` 每页把整份 PDF 读进内存上传一次；正确是两阶段——便宜启发式先筛，需重活的页一次批量跑完再按页归位。
- **缓存键漏参数**（第 2 节）；**编造的元数据**（第 5 节）；探活加进程级短缓存，同一阈值判断写两遍就该抽函数。
- **审读顺序**：`execute` 的循环体（放大在这）→ 缓存命中条件（语义错在这）→ 输出数字有没有来源。

### 6.2 自评双线
- **一条黑盒、一条静态，并行**：派 teammate 跑黑盒的同时自己 grep 旧名、读参数表、查输出上限——「过时文案与废弃参数」黑盒测不到，但会误导模型。
- **测试 agent 任务书给六样**：①源码路径与全部工具名；②两条测试通道（黑盒真调 + 白盒 `import lib/main.js` + 假 `ctx.tools.register` 收集后直接 `execute`，能注入坏参数）；③本机 node 绝对路径；④素材路径与「产物只许写某个目录」（配 `team_task_create` 的 writeScopes）；⑤报告格式：BUG 编号/严重度/复现步骤/期望/实际/证据路径；⑥「发现严重问题先单独发消息，不用等全跑完」。

### 6.3 用户说「全做」时的节奏
1. 按依赖分性能/语义/能力三组，一组改完立刻 `node --check` + 实测，别一口气写 300 行再验。
2. 性能项**先量基线再改**，改完再量热耗时；否则「优化」只是感觉。
3. 改 schema 最易误删相邻字段、多工具共享的改动先找唯一锚点（第 1 节）；改完同步 README、`插件说明.txt`、代码注释三处，注释讲「为什么这样改」，不是「改了什么」。

### 6.4 改名 / 合并后扫旧名
- **范围六处**：工具名、源码路径、缓存目录、进度条接口路径、技能文档、记忆库的事实条目；**判据**是 `grep -rn '旧名' 代码 技能 记忆库` 三处都要过一遍，只改代码不算改完。

### 6.5 体检残留六类（照单过）
1. 临时诊断日志（`appendFileSync`/`writeFileSync` 与「临时/诊断/debug」注释，看有没有删除路径）；2. 空函数与死导出（数每个导出被 `main.js` import 的次数）；3. README 与代码脱节（逐条核版本号与「默认/必须/不支持」）；4. `package.json` description 停在早期设计；5. 一次性调试脚本散在根目录、硬编码别人机器路径（没被任何入口引用就归档并注明「import 已失效」）；6. **真别动**：venv、node_modules、lock 文件、仍在被引用的备用引擎通道。
- **移除一个功能通道按五处清**：①import ②路径常量（如 `ocr-venv` 的 `venvPython`）③参数枚举与默认值（`engine` 只剩 `mineru`）④工具 description 里「失败自动兜底」的措辞 ⑤fallback 改成就地报错；漏一处＝旧通道还在兜底跑。

### 6.6 脚本说「成功」不算数
- **行数 + 残留关键词双查**：删死代码后只看脚本打印的 bytes 会被骗；`lines after` 没变就该警觉。
- **改文档别在 PowerShell 里拼**：反引号是转义符，双引号字符串与 here-string（`@"..."@`）都中招；一律用 `write` 写临时 `.mjs` 再 `node` 执行，写完用 `Select-String` 或 node 复查命中数。
- **临时脚本扩展名**：`.mjs` 按 ESM 解析，`require` 报 `not defined in ES module scope` → 改用 `.cjs`。

## 7. 自建插件的署名（2026-11-21 定，用户口径）

**默认只对新写的自建插件生效，已有的不主动回头补**；用户点名要补时才补（2026-11-21 已按用户要求给 `meow-mind` 0.1.0 与 `dsh-doc-parser` 0.3.6 补上，其余保持原样）。

新建自建插件时，`package.json` 顶层的 `author` 写成 **`姓名 · 会话码`**，与技能 frontmatter 同一格式：

```json
{ "name": "my-plugin", "version": "0.1.0", "author": "ZQY · LD-BA49BC34-894F" }
```

- **码的来源**：`<用途前缀>-<SHA1(sessionID) 前 8 位>-<后 4 位>`，详见 `C:\Users\ZQY\.dsh\CODES.md`；新会话不继承旧码，除非用户明确说继承。
- **只署自己写的**：第三方插件（`node_modules` 里装的、别人给的）一个字段都不动；判断插件是不是自己写的，看是否在 `C:\deepseek\插件\` 或 `C:\deepseek\work\` 有源码，而不是看它装在哪。
- **为什么只对新插件**：已装插件的 `package.json` 改一次就要重装/重链一次（`file:` 安装是硬链接），为一行署名动运行中的包不值；而新插件写的时候顺手就带上了。
