---
name: dsh-selfcheck
description: 给 DeepSeek Harness 桌面版做一次完整体检——内核、依赖与 bundles、三方插件、插件目录、B站 MCP、技能、长期记忆、工作区、HOME、外部通道、更新检查、使用统计共十二项，四个对话内哨兵；查完顺手对齐插件说明与记忆库，并按规定格式出报告。当用户说「自检」「体检」「检查一下环境」「升级后验收」「某个工具好像坏了」「看看有没有新版」时加载。
whenToUse: 用户说「自检」或要求检查 DSH 环境；装了/升级了内核或插件之后要验收；怀疑某个工具、记忆系统、外部通道不工作时；想知道插件或技能有没有新版时；隔了一段时间想摸清现状时；用户要求整理记忆库、核对插件与技能清单时。
---

# DSH 自检：十二项 + 四个哨兵 + 四件对账

一句话：**不许只查一两项，不许只报数字不做判断，不许把「装了」当成「能用」；自检不只是读——查完必须顺手把文档和记忆库对齐到实况（见第 5 节）。** 历次实测读数、红点样本、事故经过与版本沿革见 `evidence/selfcheck.md`（交付目录里即本案的 `evidence-selfcheck.md`），执行时不必读。

## 0. 先跑脚本（有就跑）

```powershell
$node = 'C:\Users\ZQY\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe'
$sc   = 'C:\Users\ZQY\.agents\skills\dsh\scripts\selfcheck.mjs'   # 技能内副本，优先用这个
& $node $sc --full     # 全检，约 20 秒
& $node $sc --quick    # 快检，约 9 秒
& $node $sc --diff     # 只看与上次的差
& $node $sc --only 06,08   # 只跑指定项，0.2 秒级；不落档、不做差分
# 项号：01 内核 / 02 依赖 / 03 插件版本 / 04 插件目录 / 05 B站MCP / 06 技能 / 07 记忆 / 08 工作区 / 09 HOME / 10 外部通道 / 11 更新检查（已并入 03，旧命令照跑） / 12 使用统计
# 口语→项号：只查技能和工作区=06,08 ／ 技能+工作区+记忆=06,07,08 ／ B站 cookie=05 ／ 插件版本和依赖=02,03 ／ 只看内核=01 ／ 记忆体检=07
```

> 自检脚本**只有本技能内 `scripts/selfcheck.mjs` 一份**：`C:\deepseek\tools\selfcheck\` 下的旧副本已于 2026-11-24 清掉，不再有「两份代码必须同步」的约定。它要用的 profile、`dsh.cmd`、记忆库、历史输出目录见本技能目录 `DEPENDENCIES.md`。脚本零依赖（只用 Node 内置模块 + `node:sqlite` 只读直读记忆库），多工作区由 `WS` 常量驱动（cwd 含 `.dsh-mind` 就用 cwd，否则退回 `C:\deepseek\work`）：记忆库、落档目录、可清清单、残留扫描、差分标签全部随 WS；同目录另有 `README.md`（依据见 `evidence/selfcheck.md` 第 0 节）。

结果同时打印并落档：work 会话落 `C:\deepseek\work\handover\selfcheck\<本地时间>-<模式>.json`，其它工作区落 `<当前工作区>\work\handover\selfcheck\<本地时间>-<模式>.json`；自动与**同目录**上一份比对（内核/依赖/bundles 变化、插件版本变化、体积涨落、记忆增减）。不同工作区各存各的，基线不互串——非 work 工作区第一次跑会显示「首次运行，无基线」，属正常。

**换一台机器或脚本不存在时**：按第 1 节的取数方法手查，一项都别跳。**node 不在 PATH 时**：用 DSH 运行时的绝对路径（如上），不要装 Node、不要改 PATH。

## 1. 十二项怎么查、判据是什么

| # | 项 | 取数方法 | 判据 |
|---|---|---|---|
| 01 | 内核 | `& '<部署目录>\resources\runtime\cli\bin\dsh.cmd' --version` ＋ `(Get-Item '<部署目录>\DeepSeek Harness.exe').VersionInfo.FileVersion` | 两处读数一致；说得出版本号与上一版差在哪 |
| 02 | 依赖 | node 读 profile 的 `package.json`：`dependencies` 与 `dsh.profile.bundles` | 声明了 `dsh.bundle` 的依赖全在 bundles 里；**掉队＝对应工具面直接消失** |
| 03 | 三方插件 | 逐个读 `node_modules/<包>/package.json` 的 version 与 repository | 一个不漏。**报告里必须用表格：一个插件一行、五列（插件 / 版本 / 来源 registry·link·file / 状态 正常·异常·已卸 / 一句话用途）**，**不分组**，一个插件占一行 |
| 04 | 插件目录 | `C:\deepseek\插件` 下 archives / backups / forks / patches / 活引用 clone 的体积与文件数 | 指出可清项与不可动项，别只说「正常」 |
| 05 | B站 MCP | `C:\deepseek\tools\bili-mcp`：服务端在不在、`cookie.json` 最后写入时间、**起一次真 server 列工具并真调 `bilibili_video_info`**（脚本 `--only 05` 会代跑；手查＝在该目录下 `require.resolve('bilibili-mcp-server')` 取入口，用 stdio 依次发 `initialize` → `tools/list` → `tools/call`。不想写 stdio 客户端时的替代判据：①用本会话已注入的 `bilibili_video_info` 真调一次；②`cookie.json` 的 mtime 与今天比。两条都过就算通过，两条都不行才算失败） | 工具数应为 **31**；cookie 超过 14 天必须实测；参数名是 `videoId` 不是 `bvid` |
| 06 | 技能 | user 级 `C:\Users\ZQY\.agents\skills` ＋ 各插件的 `skills/*/SKILL.md`（或单数 `skill/`、`AUDIT_PROTOCOL.md`）；枚举：`Get-ChildItem <技能根> -Directory \| ForEach-Object { $d = Join-Path $_.FullName 'SKILL.md'; if (Test-Path $d) { "{0} | {1}" -f $_.Name, ((Get-Content $d -TotalCount 12 \| Select-String '^description:').Line) } }`（脚本 `--only 06` 会代跑） | 分两节写，**每个技能都必须写「名字 + 一句话用途 + 触发场景」**；插件自带的按包分组，组内也要逐个写，只报总数不合格 |
| 07 | 记忆 | `node:sqlite` 的 `DatabaseSync(<记忆库路径>, {readOnly:true})` 直读——**七层各一张表**（`soul`/`user`/`project`/`fact`/`lesson`/`topic`/`rules`，列 `id`/`content`/`status`/`keywords`/`hit_count`/`last_accessed_at`），查 `SELECT status, COUNT(*) FROM <层> GROUP BY status`；超长查 `SELECT id, length(content) n FROM <层> WHERE status IN ('active','memory','evolution') ORDER BY n DESC`；再按第 5 节体检修正。**库路径按 cwd 优先**：当前目录含 `.dsh-mind` 就读它，否则退回 `C:\deepseek\work`（脚本输出会标「库=」） | active/all 两个数、七层分布、最长条目、超长计数（>800 / >450）、db+wal 大小；**哨兵：`memory_search` 能召回旧事实**；**体检要在本轮内修完，不许只报问题不修**。脚本末尾会打印**待人工对账**四件——看到就必须真做；超长 **>800 字**先压，>450 的多数是 topic/project 演进记录，按层判断别一律砍；脚本还会用 `sink` 字段直接复用 meow-mind 的 `findSinkCandidates` 报**沉淀候选 N 条**（最近 1 天、命中方法词、与技能正文重合 0.12–0.5），这一行回答的是「这些经验该不该写进自建技能」，与超长、重复是两回事；`sink.error` / `sink.skipped` 表示 meow-mind 没装或加载失败，不影响其余项。同一处还会用 `sink.pluginGaps` 报**插件缺口 N 个**——取近 7 天记忆里提到的代码符号（小写驼峰 / 全小写下划线 / 小写开头点分，排除文件扩展名与系统文件名），在**所有目录型 `file:`/`link:` 依赖的源码**里都找不到，就说明「记忆点名了某个函数或配置键，但自建插件里没有它」——要么插件该补这个能力，要么行为已经变了。报「无」是好事（说明记忆与源码同步），报出来是哨兵不是待办，假阳率不低，要人工看 |
| 08 | 工作区 | `Get-ChildItem -Recurse -File \| Measure-Object Length -Sum`，分到子目录。**根目录按 cwd 优先** | 点名该清的临时目录（探针、旧缓存、测试残留）；**根目录有临时 `.mjs`/`.json`/解包目录就当场清掉**（准则第十节「测试产物随手清」） |
| 09 | HOME | 同上，分到 `.dsh` 各子树（profiles / storages / attachments / speech-to-text / sessions / dsh-runtimes） | 说清哪块最大、哪块可清、哪块动不得 |
| 10 | 外部通道 | QQ 插件与凭据（**`dsh-qqbot-bridge` 2026-11-20 已卸，此项恒 false，重装后才适用**）、MinerU API 端口、bsk daemon、worktree 残留、GUI 端口（端口直接从 GUI 地址栏 `http://127.0.0.1:<port>/` 读，或用 `Get-NetTCPConnection -State Listen | Where-Object OwningProcess -eq (Get-Process -Name 'DeepSeek*').Id` 反查；验监听用 `Get-NetTCPConnection -LocalPort <port> -State Listen`）、MinerU 在不在（`Get-NetTCPConnection -State Listen | Where-Object LocalPort -eq 18000`，或 `Invoke-WebRequest 'http://127.0.0.1:18000/openapi.json' -UseBasicParsing`；旧端口 8000/8001/7860 是 community 版，2026-11-21 实测只监听 18000）、bsk 在不在（`Get-Process | Where-Object Name -match 'bsk'`）、worktree 残留（`Get-ChildItem .git\worktrees -ErrorAction SilentlyContinue`） | 断了你能先发现，不该等用户来报 |
| 11 | 更新检查 | 对每个 **registry 装**的依赖查 `https://registry.npmjs.org/<包名>/latest` 与本地 version 比；**非 registry（`file:`/`link:`/`git+`）但有 `repository` 的**，按 5.5a 查 GitHub tag（jsdelivr 直连，不用代理）；无 repository 才是「自研」。**手查的循环命令**（脚本不在时）：写一个 `.cjs` 读 `package.json` 的 `dependencies`，对每个包 `GET https://registry.npmjs.org/<encodeURIComponent(name)>/latest` 取 `version`，与本地 `node_modules/<name>/package.json` 的 `version` 比，输出「可更新 / 已最新」两列；`file:`/`link:`/`git+` 前缀的键先查 `repository`，有就转 jsdelivr，没有标「自研」 | 分「新 / 旧 → x.y.z / 自研 / 无 tag」四档（`--only 03` 已自动出）；**只报不擅自升**；红点要先说清是「真新版」还是「npm 比本地旧」；npm 的 `latest` 标签 ≠ 上游最新版（见 5.4） |
| 12 | 使用统计 | 脚本 `--only 12`（`--full` 也跑，约 6 秒）：扫 `$DSH_HOME/sessions` 近 30 天的 `session*.jsonl.zstd`，解出四类事件——`tool/call` 的工具名（按前缀归插件）与 `skill` 工具的参数名（模型自动触发）、`user/message` 里的 `<skill_content name>`（用户手动触发）、`<available_skills>`（技能目录常驻字符）、`request/header` 的 `data.header.tools`（工具 schema 常驻字符）。**会话日志是「多帧拼接」的 zstd，Node 自带的 zstd 流只解第一帧**，脚本按 magic 扫帧起点逐帧解（2026-11-24 实测 88 MB / 51780 帧零失败、1.8 秒）；换实现时别用 `zstdDecompressSync` 一次性解整文件，会只得到 198 字节。**工具面按会话漂移**（MCP 没起、插件没注册），脚本取「最全」那一档并在输出里标出区间，**别取最后一个 request/header**——2026-11-24 实测同机会话间从 19 个 / 14.3 K 字符到 143 个 / 158.3 K 字符，取最后一次会得到随扫描顺序漂移的假数字 | 常驻开销＝工具 schema 字符 + 技能目录字符 + **user-global `AGENTS.md` 字符**（2026-11-24 补，此前这项从没进过体检表）；合计超 180 K 字符时脚本打 ⚠，处置是把长内容挪进技能或样板；**30 天 0 次调用的插件与技能列表就是吃灰清单**，但要按「0 次不等于没用」处理（刚装、低频、备用的先标出来问用户，不要直接判死）；工具 top 用来判断哪类操作在膨胀上下文。**2026-11-24 补五项口径（吸收 `checkup` 的 `audit.py`）**：①**MCP 工具单列** `mcpTools` / `mcpChars`（本机按 `mcp__` 前缀只取到 0——B 站 MCP 的工具名是 `bilibili_*` 平铺，不是 `mcp__` 前缀，脚本已注明「需人工核对」，换机器时先确认口径）；②**零触发技能按 description 字符降序**（输出形如 `doc-parsing(374c), kb-ops(267c)`），吃灰榜先看谁贵；③**同名技能检测** `dupNames`（后加载的静默覆盖前面的，属故障不是配置）；④`disable-model-invocation: true` 记 0 字符（连简介都不进目录，就不该算进常驻）；⑤**硬闸门** `schema_unrecognized`＝`sessions ≥ 5 && events === 0` 时直说「日志格式可能已变，本次用量结论不可用」并停——解析失败绝不能安静地表现成「没人用」。另：hook 与后台类插件不写会话日志，它们的 0 次属**仅静态盘点**，不要当吃灰清 |

**工具面统计会漏「按需激活」的工具**：`dsh-univer-office` 的 14 个 `univer_*` 工具默认不进工具面（包内 `activationGate`，默认 `skills: true` + 12 个 office/univer 技能名；调过这些技能之一后才出现，省约 21 KB 常驻）。判断方法：宿主 `Tool.listTools` 有而模型面没有，且该插件源码里 `ctx.tools.register(tool, { when })` 带条件——那是设计，不是掉线。

**取数细则**：工作区子目录的可见阈值＝全量子目录里 ≥20 MB 或 ≥200 文件；HOME 的空间大头先看 `storages` / `attachments`（每次 API 上传的 PDF 副本、删会话不回收），nvidia 库与 `mineru4-venv` 动不得（`mineru3-test` 旧 venv 自 2026-11-25 起不再被引用，可删）。体积数字以本轮 `--full` 实测为准，不凭印象。阈值与口径的历史变动依据见 `evidence/selfcheck.md` 第 1 节。

## 2. 四个对话内哨兵（脚本证明不了，必须真调一次）

1. `memory_search` 用任意一条**你确信在库里**的关键词能召回，且返回条目内容正确 —— 记忆系统活着；搜不到先换更泛的词再判，**不要把「作者记忆里的某条具体事实」当固定样本**（换机器、换工作区不一定有，会误判成检索坏了）。
2. 本轮记忆注入横条可见 —— 注入链路活着。**若本轮没有注入块但 `memory_search` 正常，判为「关键词未命中」，不算故障**；要强验证就开个新会话看首轮有没有横条。
3. 文档链 —— **看工具面里 `univer_*` 那一组在不在**（新建/状态/导出/截图…），配合第 02 项确认 `dsh-univer-office` 在 bundles 里即可。**禁止用 `univer_new` 建探针文件**（原因：会弹文档窗、锁文件、`%TEMP%` 被拒，依据见 `evidence/selfcheck.md` 第 2 节）
4. QQ 侧真发一条消息看有没有回 —— 远程通道活着（QQ 桥未装时跳过，见第 10 项）

脚本 `--full` 已经自动做了 B站 MCP 的起 server + 真调，所以哨兵里不再重复。

## 3. 报告格式（硬规定）

1. **三方插件逐个**写「版本号 + 是否最新 + 一句话用途 + 状态」，不能只报数字，不能合并成一行。**版本列必须带最新判定**（2026-11-24 用户要求）：与上游同版或本地领先写「**新**」，落后写「**旧 0.1.22 → 新 0.1.23**」，自建无上游写「**自研**」，有仓库但仓库没打 tag 写「**无 tag**」。脚本 `--only 03` 已自动出这四态（registry 查 npm latest，查不到的按 `package.json` 的 `repository` 查 GitHub tag，见 5.5a），报告直接抄它的判定，不要凭印象手写「应该是最新」。
2. **B站 MCP 单独一节**，按功能分组列全部工具名。
3. **技能单独一节**，分 user 级与插件自带两类。**每一个技能都要写「名字 + 一句话用途 + 触发场景」**——用户 2026-11-09 明确要求「三方技能附上简介」；只列名字、只给数量、把一组压成一行都不合格。
4. 其余每项都要带一句「**这意味着什么**」。
5. 坏消息不许省略，也不许藏在最后一行；结论放末尾。
6. 第 5 节的四件对账做了什么、改了什么，要在报告里单独交代一段（改了哪几处、为什么改）。
7. **使用统计单独一段**（第 12 项）：常驻开销两个数（工具 schema / 技能目录）、30 天被触发的技能数、零触发清单、插件调用次数、工具 top 前几。**要说出这意味着什么**——常驻字符涨了是哪类工具变多，零触发是吃灰还是备用，别只贴数字（2026-11-24 用户要求「版本列加是否最新」时一并定的口径）。

总判据：**读报告的人不查任何东西，就知道每个组件是干什么的、哪里不对、下一步该动哪里。**

## 4. 异常速查（症状 → 先查什么 → 常见修法）

| 症状 | 先查 | 常见修法 |
|---|---|---|
| 某个 `memory_*` / 插件工具报 `unknown tool` | 该包是否还在 `dsh.profile.bundles` | 手工补进 bundles，热重载即回；不用重启 |
| 插件装完但工具面没出现 | deps 有、bundles 没有；或客户端半没刷新 | 补 bundles；客户端半 `Ctrl+Shift+R` |
| 内核更新报 `Host did not complete graceful task teardown … SIGTERM` | 是否有子进程（MCP server、billion、vite 等）没退出 | 用电源键完全退出再开；pending 里的安装包会自动接上 |
| 模型请求 502 / 503 / 500 | `api.deepseek.com` 连通性、系统代理状态 | 上游过载，等一会儿重试；别改本地配置 |
| `memory_search` 报「短 id 命中多条」 | 是否用了截断 id | 用完整 id |
| PowerShell 读中文 package.json 报「传入的数组无效」 | 是否用了 `ConvertFrom-Json` | 改用 node 读，别信 PowerShell 的 JSON |
| 面板提示的插件版本高于 npm latest | 先看装法：`file:`/`link:`/`git+` 还是 registry；再查上游 releases | 非 registry 装的**以上游 releases 为准**（npm latest 可能停在旧版，面板不是误报）；只有 registry 装的才以 npm 为准 |
| MinerU API / bsk daemon 没起 | 是否刚重启过 DSH | 属预期，按需手动起（`mineru-api.cmd start`、`bsk daemon start --foreground`） |
| `failed to prepare profile bundle` / 插件工具全消失 | vendor 与 `node_modules\<pkg>` 两侧的文件数 | 0 文件空壳目录（`pnpm install` 不会修）→ 删掉重装；手工换目录要「`.new` + 原子改名」，**别先清空目标** |

## 5. 自检必须顺手完成的对账（5.1–5.5，沿用「四件」旧称）

自检不只是「读」，也是一次**对账**：查完必须把下面各处对齐到实况，**当轮改完再出报告**。5.4 / 5.5 是后来追加的两个子任务，标题里的「四件」是旧称，条目以本节 5.1–5.5 为准。

- **5.1 插件说明（`C:\deepseek\插件\插件说明.txt`）**：改第一（基准：内核版本、实装规模 26 deps / 38 bundles——以本轮实测为准，装/卸插件后会变）、二（实装表：逐包版本与用途，删已卸载、补新装）、三（目录结构：archives / backups / forks / patches / 活引用 clone 的文件数与体积）、五（补丁：哪几组、怎么重放、有没有因插件升级而失效）、六（待办）五节。**判据**：文件里出现的每个版本号，都要能从 `profiles\desktop\package.json` 或 `node_modules\<pkg>\package.json` 核到；核不到的就是上一轮留下的旧值，改它。**改版本号不要全局替换**：只改实装表那几行，改完 grep 历史区核对——历史记录里的旧版本号是证据，不是错误（lesson `0mwiu57z`）。上次同步的基准读数与 2026-11-09 的事故经过依据见 `evidence/selfcheck.md` 第 5.1 节。**本机没有这个文件就跳过本节并在报告里注明「本机无插件说明文件」，不要凭空创建一个。**
- **5.1b 插件说明的五节怎么写**（照这个骨架，别自由发挥）：一、基准——`更新：<YYYY-MM-DD HH:mm>（北京时间，<这次干了什么>）` + 内核 / 桌面 / Electron / cordis / 运行时 node / pnpm / python 各版本 + `实装（<N> 依赖 / <M> bundle）`；二、实装表——一插件一行五列；三、目录结构——archives / backups / forks / patches / 活引用 clone 各自的体积与文件数；五、补丁组——每组写「脚本路径 / 失效症状 / 重放时机」；六、待办——带日期的编号列表。第四节按需（当前是旧的 API 变更记录），没有就写「无」。

- **5.2 记忆库体检与修正（`<工作区>\.dsh-mind\memory.db`）**：不只统计，当场修。四类问题各对应一种修法——超长（一般 >800 字，topic 除外，按 `length(content)` 排序找）：拆成两条聚焦条目、旧的设 `review`；重复 / 被新事实取代（同一主题多条、版本号互相打架）：合并成一条新的（保留最新结论）、**把旧的设 `review`**，不许新旧并存；过时（已废弃功能、旧版本行为、被推翻的判断，版本号 / 路径 / 结论与当前实况不符）：更新内容，整条失去意义就 `review`（旧三态 `archived` 在 meow-mind 里映射到 `review`）；关键词不准（注入的条目与当前话题无关）：`memory_update` 只改 `keywords`。**判据**：一轮自检结束时，报告里能列出「本轮改了什么、为什么」，且库里没有新旧两套描述并存；**六态**＝`observation`/`evidence`/`candidate`/`memory`/`review`/`evolution`，查数口径 `status IN ('active','memory','evolution')`（旧库才有 `active`）；写法按记忆系统规则（fact ≤60 字、lesson 一条一教训、topic ≤300 字、keyword 8–13 个）。**不许为了凑数归档**：仍在用的 decisions/lesson 不要动，只有被新总结真正吸收或确认过时才降级。
- **超长口径不一致**：`over` 按七层 union 统计 `>800`／`>450`（含 `project`），`longest` 只取 fact/lesson/topic/rules 四层——报告「超长 2 条」而最长三条都 770–780 时按 `longest` 判，别当数据错。
- **5.2b 换记忆插件后脚本静默输 0，先查三处口径**：①脚本读哪个库（WS/MEMDB 常量常硬编码旧目录名）；②SQL 里的 status 字面值（旧库 `active`、新库 `memory`／`evolution`，查到 0 条照样打印）；③汇总用的层名与表名（七层 + 附加表，没有 `memories` 表）。判据＝拿一条已知条目在新库里端到端搜到。
- **5.3 本 SKILL.md 与 `selfcheck.mjs`**：本 SKILL.md 只在**流程本身**变了时改（新增检查项、哨兵换了、判据变了、报告格式变了）；`scripts\selfcheck.mjs` 只在**取数方式**变了时改（新路径、工具数变化、新冒烟）。**只有这一份脚本**：`C:\deepseek\tools\` 下的旧副本已于 2026-11-24 删掉，原先「两份副本 md5 必须一致、以 mtime 较新为准」的约定同时作废；改完跑一次 `--quick` 验行为即可。当前脚本的字节数与改动项依据见 `evidence/selfcheck.md` 第 5.3 节。
- **5.4a 更新检查·插件**：两件事——**插件有没有新版**、**技能有没有跟着失效**。插件只对 **registry 安装**的包查 `https://registry.npmjs.org/<包名>/latest` 与 `node_modules/<包>/package.json` 比，registry 直连可用、**不需要开代理**；`file:` / `link:` / `git+` 装的包在 npm 上没有对应版本，**不要拿 npm 的 latest 去比**（会报出「0.6.2 → 4.5.1」这种假降级），归到「不在 registry」一档，需要时再单独查 GitHub releases（那一步要开代理，见 5.5）。
- **5.4b 更新检查·红点与 latest**：**红点有三类成因，先说清是哪一类再决定升不升**：①`file:`/`link:` 本地装，npm 查不到 → 必然红；②`git+` 装，检查器访问 GitHub 直连失败报 `ECONNRESET` → 红；③npm 的 latest **比本地旧**（我们从 GitHub release 装的）→ 点「更新」会**降级**。判断顺序：先读 profile 依赖来源再决定；`file:` / `git` 装的一律点「不再提醒」。**npm 的 `latest` 标签 ≠ 上游最新版**——只在 GitHub release 发版的包，npm latest 可以长期停在旧版而面板红点一直亮；凡 `file:`/`link:`/`git+` 装的包，判断有没有新版必须另查 GitHub releases / tags，不能只看 registry。三类样本与具体版本号依据见 `evidence/selfcheck.md` 第 5.4 节。
- **5.4c 更新检查·更新说明 / 技能 / 规矩**：**汇报时必须附更新说明**——说某包「可更新 / 已升」时，同时给出它这一版改了什么：①GitHub `releases.atom` 的 `<content type="html">`（不占 API 60/h 配额，实测能拿到完整 Features / Fixes / Commits）；**优先用它，别用 `api.github.com/repos/<o>/<r>/releases`**——未认证每分钟 60 次，2026-11-24 就这样连查两个包撞了 403。确需 API 时带上本机凭据工具里存的 token：`"protocol=https`nhost=github.com`n`n" | & 'C:\Users\ZQY\AppData\Local\Programs\Git\mingw64\bin\git-credential-manager.exe' get` 里 `password=` 那一行（`gho_` 开头、40 位，GCM 浏览器登录时存下的），请求头加 `Authorization: token <它>`，配额从 60/h 变 **5000/h**（同日实测：未认证 remaining 58 / 带 token remaining 5000）；②无 release 时对比新旧 tarball 的文件与关键内容差异；③两者都拿不到就写「无更新说明」，**不许自造、不许拿版本号搪塞**。**技能**：自写技能没有远端版本，检查的是**引用是否还有效**——SKILL.md 里提到的工具名、脚本路径、插件名是否还存在（插件卸载或改名后最容易断）；插件自带的技能随插件版本走，插件升级后要重看一眼，尤其工具名有变时。**规矩**：只报告，**不自动升级**——升级属于「动环境」，必须用户点头；升级只认 `latest` 标签，别跟 `pr` / `master`（作者 CI 会给每个 PR 发预览版、`master` 是主干快照，版本号都是 0.0.x 且随时变）。
- **5.5a GitHub 源检查·范围与做法**：5.4 只覆盖 npm registry，`file:` / `link:` / `git+` 装的包要靠这一步补——它们恰恰最容易悄悄落后。**范围**＝`package.json` 里有 `repository` 字段的非 registry 包；`link:` 装的自研包没有 `repository` 时**先查 5.5b 的已知上游表**——表里也没有、确认是自己维护的，就在报告里写「自研无上游」并跳过本步（当前清单与个数依据见 `evidence/selfcheck.md` 第 5.5 节）。**做法两通道，先用 ①**：① **jsdelivr 直连（不用代理，1 秒级）**：`GET https://data.jsdelivr.com/v1/packages/gh/<owner>/<repo>` 返回 `versions[].version`（来自仓库 tag，最新在前），与本地 version 比最高 tag → 「新 / 旧 → x」；`versions` 为空＝仓库没打 tag，写「无 tag，无法判定」。2026-11-24 实测四个仓库 1 秒内返回，**Clash 不开也能查**；脚本 `--only 03` 的非 registry 判定走的就是这条。② **GitHub API 走代理**（只在要更新说明 / commit 对比 / 无 tag 仓库时用，约 20–30 秒）：a) 先看 Clash 是否已在跑（`Get-Process -Name 'clash*'`），**没跑才启动**（`$clash = (Get-Command clash-verge -ErrorAction SilentlyContinue).Source; if (-not $clash) { $clash = 'C:\Program Files\Clash Verge\clash-verge.exe' }; Start-Process $clash`——本机是后者，换机器先 `Get-Command clash*` 找），启动后等 **12 秒**预热 + 轮询端口 7897 通（6 秒常常还没监听；轮询写法 `1..20 \| % { if (Get-NetTCPConnection -LocalPort 7897 -State Listen -ErrorAction SilentlyContinue) { 'up'; break }; Start-Sleep 1 }`）；b) 请求显式带 `-Proxy 'http://127.0.0.1:7897'`（进程内走代理，不改系统注册表）；c) 有 release 的查 `repos/<o>/<r>/releases/latest` 的 `tag_name`，404 再查 `/tags`；要更新说明就走 `releases.atom`——每条 entry 的 `<content type="html">` 就是 release 正文（Features / Fixes / Commits 齐全），不占 API 配额、403 限流时照样能用；d) `link:` 装的查 `repos/<o>/<r>/commits?sha=<default_branch>`，与本地 `git -C <dir> log -1 --format=%h` 对比；e) 用完**等 4–5 秒再杀 Clash**（用户原话「clash 软件启动要时间预热，别关那么快」）。
- **5.5b GitHub 源检查·判据与已知上游**：tag 去掉前导 `v` 与本地 version 比，不一致 → 报「有更新」并附发布时间；本地是老版本、release 页有新版 → 升级要重下 tgz + **重放插件补丁**（StudyHub 每次升级都得跑 `skills\dsh\scripts\studyhub-preset-patch.mjs`，否则「学习模式」预设标红）；`package.json` 没有 `repository` 的包先查**已知上游表**，表里有就按它查 releases，表里没有才写「查不到来源」，**不要猜**。已知上游表（手工维护，遇到新包补一行）：`@local/dsh-knowledge-base` → `KingsleyAsher/Personal-Knowledge-Base`（作者未在 package.json 写 repository；npm latest 长期不动、只发 GitHub release；当前已从 profile 卸载，条目留作重装时查上游）；`dsh-raw-html-v2` → `plolpl789/dsh-raw-html-v2`（package.json 无 repository；本地是 `C:\deepseek\插件\dsh-raw-html-v2` 的 git clone，origin 指向它，head `2591ae6` 2026-10-08；**该仓库没打 tag**，jsdelivr 返回空，判新版要对比 commit，走 5.5a 的通道②）；`dsh-doc-parser` → 无上游（自研，`C:\deepseek\tools\dsh-doc-parser` 自己维护，不需要查上游）；`meow-mind` → 无上游（自研，源码在 `C:\deepseek\work\meow-mind`，改完同步到 profile）。

## 6. 不许做的事

- 不许只报数字：每项都要给判断。
- 不许把「装了」当「能用」：能真调的必须真调。
- 不许凭印象说体积/占用：必须逐目录实测。
- 不许漏掉技能简介：只列名字等于没报（用户明确要求「三方技能附上简介」）。
- 不许把插件清单写成一串「A 0.3 / B 0.4 / C 0.5」的段落：必须用表格，一个插件一行、五列（插件 / 版本 / 来源 registry·link·file / 状态 正常·异常·已卸 / 一句话用途），**不分组**。
- 不许只报记忆问题不修：体检的结果必须落到库里的实际改动。
- 不许动「不可动」清单：nvidia 库（GPU ASR）、`插件\dsh-raw-html-v2`（活引用 clone）、`tools\mineru4-venv`（MinerU 4.x 通道 + PDFium 兜底）、`tools\sci-venv`（历史变动依据见 `evidence/selfcheck.md` 第 6 节）。
- 不许在用户没同意时清理或升级任何东西——先报，再等指令（记忆库体检修正属已授权范围，可直接做）。
- 不许只报「有新版」就动手：更新检查只出报告，升级要用户拍板。
- 不许把 npm latest 当成上游最新版：非 registry 包只看 registry 就下结论「已最新」＝漏报；也不许把面板红点当误报一键忽略——先分清是本地装、git 装还是 npm 落后（见 5.4）。
- **版本号不止 npm 一种形态**：交付形态有 npm 包、release 附件、tag 未发版代码、预编译产物四类，各自版本号各走各的；先列清这个包以哪种形态交付，再逐个核，只核 registry 会漏附件与 tag 的差异。
