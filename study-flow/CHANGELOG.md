# CHANGELOG

## 2.7.34 — 2026-11-26 · 按目标结构重排：加读序 / 停止条件 / 收工清单

诊断报告（`C:\deepseek\调研\技能梳理\study-flow-重写方案.md`，903 行）的核心结论不是「哪里写错了」，而是「**缺三段结构**」——全局没有读序（读者只能从头读到尾）、没有停止条件（感觉不对劲还继续）、没有收工清单（一讲结束漏记作答是常态）。SKILL 从 146 行重排成 **183 行**，缩 18 行内容、加三段。

### 新增三节

1. **§零 怎么读这个技能**——三条读法（第一次开课 / 已经在带 / 只问一件事）+ 最小读集（`01` / `02` / `03` 三篇覆盖 80% 日常，其余按需查）。原来没有读序，读者面对 11 篇 references 不知从哪进。
2. **§四 停止条件**——五条「任一条成立就停，先问学习者」：同一道题讲两次还不会（是前置缺环，不是讲法问题）/ 连错三道以上（回测更早章节）/ 要改进度表而这门课不是本会话在带 / 要删或归档任何学习数据 / 五问里有没答的。这些判据原来散在 `02:17-24` 与 `03:82-89`，SKILL 自己没写。
3. **§五 收工清单**——一讲结束后按顺序核五条：作答记了没有（**带 `--confidence` 吗**）/ 进度表更新了没有 / 复习全书那段写了没有 / 该出的文件出了没有 / 能力带变化改了没有。第一条最容易漏，而漏了之后 `03-review.md` 的「连续 unsure 两次就返工」永远不触发。

### 重排

- 原 §零「先看地图」与原 §一「分流」各留一节，但补了一句「按用户原话找行，不要按自己的判断挑技能」的后果说明（选错不报错，只会少做摸底与回测）。
- 「完整链路」的 0 五问→10 复盘保留，补两处：步 2 摸底加了「**交了要给能力带**」（2.7.33 加的能力带原来只写在 `01-start.md`），步 6 写全书标明「本会话直接写文件（不调插件）」。
- 分篇索引表加了「行」一列，读者能一眼看出哪篇长哪篇短。
- `scripts/qbank.py` 那行补上 `--confidence`（这是 2.7.33 最要紧的漏洞：`02-lesson.md:12` 写着「答之前让他标确信/不确定」，`grade` 命令却从来不写这个参数，字段恒为空）。
- `scripts/render_study_pdf.py` 那行补「**只出 `.tex` 不出 PDF**，写别的后缀会直接报错」——原来没提，照做的人会得到一份改了后缀的 LaTeX 源码。
- `doc_check.py` 那行补「子命令名也验、正文裸 `python` 也扫」（2.7.32 加的两把尺子）。
- 铁律表加第三行「错题」（原来标题说三条、表里只有两行）。

### 没做的（与报告不一致的两处）

- **没删 `references/10-cards.md`**：报告说它 100% 与 `html-card` 重合，但它有三样 `html-card` 没有的东西——字号下限表（**实测**低于这个数用户会直接说「字小」）、浅底配色定稿值、讲解型卡的交付前三查。删了这三样就只剩通用手册。改成在 SKILL 里写明分工：通道选路走 `html-card`，讲解型卡的参数走这一篇。
- **没把 `CHANGELOG.md` 移出技能目录**：搬走就没人找得到，改成在 SKILL 顶部注明「版本号见 CHANGELOG 顶部」。

### 验证

`doc_check.py` **209 处引用全对上**（重排前 207）；`selftest.py` **30 步 30 OK，整条链跑通**；残留 `第 9 节` 0 / `六问` 0 / `organize` 0 / `cv2.putText` 0。

## 2.7.33 — 2026-11-25 · 从 LearnHarness 调研里搬来两条判据

读了 `C:\deepseek\调研\LearnHarness-调研.md`（B 站视频提到的 AI 私教应用，343 行调研）。它第 6 节列了 12 条可借鉴机制，逐条对照本技能后**只有两条真缺**——其余要么已有，要么根本搬不动（它靠「这一阶段拿不到某个工具」和「UI 展开/折叠」保证顺序，我们只有 prompt，没那个约束力）。

### 一、摸底后必须交「能力带」

`references/01-start.md` 步 2 + `assets/progress-template.md`

原来摸底出 6–8 题、打四档就往下走。四档只说「这题答没答对」，说不出「他能推到哪里」。

新增：摸底完每个知识领域写一行三栏——**能可靠推理到 / 走到哪推理就断了 / 还没测**。写法要求「能可靠推理到」写他做得出什么（不是「会线性代数」）、「断了」写第一处卡住的地方、**「还没测」宁可留空也别猜**。判据：把这行念给没参与摸底的第三个人，他能不能据此判断「从哪开始讲、哪里可以跳」。

模板同步加 `## 能力带` 一节，写明它是**边界描述不是分数**，下一讲开场先读它。

### 二、题量的计量单位是决策点

`references/03-review.md` 第六节

「一次 5–8 题」原来只按题面数算。新增口径：**一道题里有几个必须自己判断的岔口，就是几个检索事件**——选哪个方法、算中间量、定符号与边界各算一个。五道一步到位的题＝五个检索事件，一道三步长题也是三到五个。

判据：一道题里只剩「代入公式算数」，它就没有区分度，别拿它凑数。

### 没搬的两条

| 机制 | 为什么不搬 |
|---|---|
| 阶段即工具边界（探测阶段物理上没有 `quiz` 工具） | 我们只有 prompt，没有工具层约束；写进文档也只是更严格的叮嘱 |
| 位置由带 `nodeId` 的题派生 | 要给题库加 schema、改 `qbank.py`，等于把技能改成应用，投入产出比不划算 |

回归：`doc_check.py` 202 处参数引用全过、`selftest.py` 30 步全绿（本次只动文档，未碰脚本）。

## 2.7.32 — 2026-11-22 · 两个独立审查员报的 28 条，P1 全修

派了两个只读子代理按域查（文档一致性 / 脚本实证），**28 条里 7 P1、21 P2，两域零重叠**。
本轮修 7 条 P1 + 6 条关键 P2。

### 文档（11 处）

| 位置 | 原来 | 现在 |
|---|---|---|
| `references/03-review.md:25` | 状态只四种（未讲/讲完/待复习/待返工） | 五档，补「待验证」及其切换规则 |
| `references/01-start.md:32` | 四步＝十步法第 0/1/2/3 步、导材料是步 4 | 四步＝第 1/2/3/4 步、导材料是**步 5** |
| `references/07-environment.md:87,136` | `python -m pip …`、调用一律 `python <脚本>` | 两处改 `& $PY` |
| `README.md:11-21` | 快速开始三条裸 `python` | bash→powershell、先定 `$PY`、三条 `& $PY` |
| `SKILL.md:74`、`01-start.md:72`、`03-review.md:133` | `due` / `pick` / `--kind errors` 缺必填参数 | 三处补 `--course`；`01-start` 的退出码语义纠正（漏参是 2、题库空才是 1） |
| `references/09-local-store.md:59-60` | ```bash 围栏里写 `PY=python` | ```powershell、sci-venv 全路径、`& $PY`、反引号续行 |

### 脚本（6 处）

- `qbank.py` 错题本回执：原来让读者 `python render_study_pdf.py <md> <out.pdf>`——既没 `--kind errors`、
  又会得到一个**改了后缀的 LaTeX 源码**。改成明写两步（先出 `.tex` 再 `compile_study_pdf.py`）。
- `qbank.py` 的 `stats` 回执、`init.py` 两条提示、`doc_check.py` / `selftest.py` 的 docstring：裸 `python` → `& $PY`。
- `render_study_pdf.py` 加输出后缀校验：不是 `.tex` 直接退出并说明原因，不再默默写出改后缀的源码。
- 五个脚本的 docstring 改 raw string（`\s` 之类曾触发 `SyntaxWarning`）。
- `check_env.py` 的 `PIP_HINT` 改 `& $PY`，并**新增 `kb.cli` 检查**——配了不存在的路径现在会 WARN，
  不再只报「知识库 OK」让人以为是库的问题。
- `config.json` 的 `kb.cli` 从不存在的 `_kb\kb.py` 改成 `_kb\kb.cmd`。

### `doc_check.py` 加两把新尺子

原来它自报「只验参数名存在」，实测盲区比自认的宽：

- `script_model()` 本来返回 `(flags, subs)`，但检查处写的是 `flags, _ = models[name]`——**子命令名被丢掉**，
  于是 `qbank.py lst`、`qbank.py due --n 5` 这类都能静默通过。现在 subs 用上了，子命令名写错会报。
- 新增「裸 python」扫描：扫 13 篇文档（CHANGELOG 除外，它是历史证据）+ 9 个脚本的字符串常量，
  命中 `python scripts/...` 或 `python -m ...` 就报。加上这条它自己就先抓出了 `check_env.py` 的一处。

### `selftest.py` 从 26 步到 30 步

补 plan 与 day 两种 kind（原来只跑 errors 与 knowledge，等于「计划」与「每日课」这两种产出从没被自测过）。
实测 **30 步 30 OK / 0 FAIL / 27.6s**。

### 回归

- `doc_check.py`：13 篇文档 · 9 个脚本 · 166 处参数引用 · **202 处命中 · 0 问题**。
- `selftest.py`：**30 步全过**（含新加的 4 步）。
- 全部 9 个脚本 `py_compile` 无警告。
- `SKILL.md` 七节结构未动。

### 仍未修（都在 P2，记录在此）

进度目录 `学习进度\` 与 `<progress_dir>` 两套写法并存（十余处）；「知识清单八项」在 `SKILL.md` 与
`06-output.md` 指的不是同一件事；`build_kb.py --list` 会对任意 sqlite 建表；`--map-config` 路径写错抛英文
traceback；`cmd_stats` 不分档打印而 `03-review.md:115` 说给。

## 2.7.31 — 2026-11-22 · 按 skill-authoring 审议后修两条 P1

审议发现两处「照着做就会错」的问题，只改这两条，结构不动。

### 一、命令自包含：裸 `python` 在本机跑不起来（P1）

实测 `python scripts/doc_check.py` → **exit=9009**，报
`Python was not found; run without arguments to install from the Microsoft Store…`
——`Get-Command python` 指向 `C:\Users\ZQY\AppData\Local\Microsoft\WindowsApps\python.exe`（应用商店占位程序）。
换 `C:\deepseek\tools\sci-venv\Scripts\python.exe` 跑同一条命令 → exit=0、`全部对上（203 处引用命中）`。

9 处命令全部改成 `& $PY scripts\xxx.py`，并在 `SKILL.md` 第六节给出 `$PY` 的定义与「换机器就换成你自己的解释器」说明：

| 位置 | 处数 | 改法 |
|---|---|---|
| `SKILL.md` 第六节 | 2 | `$PY` 定义块 + 两条自检命令 |
| `references/04-kb.md` 第六节 | 4 | 建库四条命令，并在块前注明 `$PY` 见 SKILL.md |
| `references/08-sharing.md` 安装三步 | 2 | `init.py` / `check_env.py` |
| `references/09-local-store.md` | 0（原本就用 `$PY` 但从未定义） | 开头补一句出处 |

### 二、触发边界：漏了新邻居、只排了 3 个（P1）

`description` 原来只排除 `study-tutor` / `study-book` / `study-intake`，而插件 5.1.0 新增的 `study-coach-team`（私教 + 4 助教）与 `study-self`（一句话建自学课）、`study-custom`（大书定制）都在同一触发面上抢。

改法：**砍三个低区分度触发词**（「继续上次那门」「周复盘」「这门还差多少」，它们是流程内部动作、不是入口），**补三个边界**（study-self / study-custom / study-coach-team）。369 → **432 字符**，仍在 500 以内。

### 三、config.json 加排除说明（P2）

`config.json` 里 5 个本机绝对路径（`study_dir` / `progress_dir` / `kb.db` / `kb.cli` / `texlive_bin`），`.gitignore` 只挡 git。在 `08-sharing.md` 安装三步后加一段：打包分享前手工删掉它，让对方跑 `init.py` 自己生成。

### 未做的两条 P2

- 正文仍缺「交付前验收」清单（有 8 条禁区、缺「怎么算干对」）；
- `06-output.md` 191 行贴 200 行上限。

两条都不致命，等下次动那两篇时一起处理。

### 回归

`doc_check.py` **203 处引用全对上**、`selftest.py` **整条链跑通了**（26 步）；裸 `python` 命令剩余 **0 处**；11 篇 references 与 9 个脚本仍全被 SKILL.md 提到。

## 2.7.30 — 2026-11-22 · SKILL.md 结构重排：三张分流表合一、地图前置、链路补上五问

入口这一篇越改越厚之后出现了结构性问题：三张表在做同一件事（任务→篇、说法→条、文件→管什么），地图排在三张表之后，十步法从「定终点」开始——开课五问根本没有位置，而 `01-start.md` 的第一件事就是问五问。**references 一篇未动**（编号与内部结构都是清楚的），只重排 `SKILL.md`。

**结构**（7 节，`## 先分流` 与 `## 入口会撞车` 已合并，`## 一、…` 到 `## 六、…` 重新编号为 `零`–`六`）
- `零、先看地图`：四层表 + 磁盘布局前置（原来是第 47 行才出现）；磁盘布局里的 `学习进度` 改成 `<progress_dir>`，与 `03-review.md` 统一口径。
- `一、分流：手上是哪件活`：一张 11 行表，列是「用户说 → 读哪篇 → 不归我的时候」，把原来的三张表压成一张；开头加了「按用户原话找行，不要按自己的判断挑技能」。
- `二、完整链路`：十步法补上 `0 五问`，原 0–9 顺延为 1–10；表头写明「第 0 步不是可选项」；末尾一句「步 7 是循环，其余每步只做一次」（原来这段在「六、最短路径」里，现并入）。
- `三、分篇索引` / `四、脚本索引`：原来合在「四、子技能与工具」一节，拆成两张表。
- `五、铁律与禁区`：铁律表补齐第三条「错题」（原来标题说三条、表里只有两行）；禁区 8 条不变。
- `六、自检`：`selftest.py` 与 `doc_check.py`，连同「这两个工具自己也会漏」的说明。

**删**
- `## 六、一次完整教学的最短路径`——它是十步法的压缩版，内容已并入第二节。

**验收**
规模 6925 → 6687 字符、145 → 142 行（少掉的全是重复）；`description` 一字未改（369 字符）；11 篇 references 与 9 个脚本在文中全部提到；抽查 16 条关键判据全在；旧的四个标题（`## 先分流` / `## 入口会撞车` / `## 六、一次完整教学的最短路径` / `## 二、三条铁律`）已查不到；正文无 `C:\` 绝对路径。`selftest.py` 26 步 26 OK，`doc_check.py` 203 处引用全部对上。

## 2.7.29 — 2026-11-22 · 并进 good-learning 的八条判据，study-flow 接管备考

`good-learning`（第三方，MIT，348 stars）与 `study-flow` 同源：两个 PDF 脚本的 docstring 逐字相同、三种导图与 `--map-config` 都在本技能里。它剩下的价值只在八条判据，现已全部并进来，此后由本技能单独承担「从头学」与「备考」两种场景。

**新增**
- `references/11-exam.md`：备考章全文——进备考模式的三个判据、诊断问卷五问、差距的表述方式、备考计划五要素（时间轴 / 五类时间 / 每天任务与验收产物 / 指标与调整规则 / 缺失材料影响）、模拟与真题怎么用、找书的四条判据、什么时候才重排。

**改**
- `SKILL.md` description：删掉「不用于考试备考排日程（见 good-learning）」，加上「有明确考试日或目标分数要排备考计划时（见 `references/11-exam.md`）」——不改入口，补了判据也接不到备考请求。
- `references/06-output.md` §四：知识清单那段补**两个状态标记**（范围待核 / 掌握待测）；学习计划那段补一句「备考场景在六项之上再加五类时间与调整规则，细则见 `11-exam.md`」。
- `references/02-lesson.md`：第一节前加「每讲第一句先摆今天的目标与时间预算」；「讲一段」那条补「零底座课程的入门核心例题单独起页」。
- `references/03-review.md`：周复盘五步 → 六步（新增「结束四问」，原第 5 步顺延为 6）；周复盘末尾补「跨天保留进度，不因一次失误大幅重排」；新增 `## 七、错题本` 七条硬要求（首页直接第一条、七件事、错因只在有证据时填、六分类、可打印勾选框、不会做与做错分开、模拟不进掌握度）。
- `assets/progress-template.md`：状态四档 → **五档**（加「待验证」——讲完但还没做过题、或模拟成绩还没核实）。

**外部**
- `good-learning` 的 description 加了「已被 study-flow 覆盖」前缀（文件保留，降权不抢触发）。

**验收**
`11-exam.md` 6 节；`06-output.md` 出现 `11-exam.md` 引用 1 处、`11-exam` 在 `SKILL.md` 里 1 处；`03-review.md` 出现 `## 七、错题本`；`progress-template.md` 状态五档；`SKILL.md` 版本行 2.7.29；全目录无 `good-learning` 的「不用于」引用残留。

## 2.7.28 — 2026-11-22 · 从 dsh-daily-flashcard 5.3.3 搬来三条硬判据

调研对象：`@ericwang1358/dsh-daily-flashcard` 5.3.3（本地 tgz 安装；npm 上 latest 仍停在 4.13.0）。

- **`scripts/qbank.py add` 新增 `--quote` / `--verify`**：`--quote` 存逐字引文（item 新字段 `quote`），`--verify <原文文件>` 去掉全部空白后按子串核对。四种状态实测：对得上无提示 / 对不上报「引文在原文里找不到」/ 只给 `--quote` 报「还没和原文比对过」/ 不给 `--quote` 与旧行为完全一致。`--strict` 下对不上直接拒写（exit 1）。新函数 `check_quote(quote, corpus)`，`audit_row` 加可选 `corpus` 参数。`py_compile` 通过，文件 39468 字符。
- **`references/02-lesson.md` 补两条纪律**：①引文必须过 `--quote` + `--verify`——原来只有一句「引文必须逐字对上资料」的文本要求，程序从不比对；②**作者自查不算批准**——一组题收完派只读子代理冷读，只给题目与六条判据、不给判断依据与出题思路，没有子代理可派时隔一轮独立过一遍，记录里写「自查」不写「已验收」。
- **`references/03-review.md` 补「题量是上限不是配额」**：材料撑不起 8 道有区分度的题就只出 5 道——为凑数拆知识点、把一句话拆成两问、加一道「以上都对」，比少出几道更坏。

**没搬的三类**（记档备查，不是遗漏）：①独立 reviewer 的第二次模型调用——它有自己的 provider 预算，我们全程在会话内，只能改子代理；②inventory + fingerprint + 版本存档——依赖 StudyHub 的 source record / page id / job 与存储；③覆盖率面板 `Concepts covered N/M` 与草稿发布流——同属它的数据模型。

**调研里值得记住的两条**：它的 `lib/one-pass/limits.js` 九个限额每个都写着「原型试过多少 → 为什么定这个数」（如 9000 字符是试过 24000 后回包截断整份丢、`reviewBatch: 7` 是一批 18 张时回包被标 invalid）；`lib/one-pass/checks.js` 十三项程序检查全不花模型 token（选项打乱用 Fisher–Yates、正确项位置由程序定、引文必须落在声称的那一节）。

回归：02-lesson 5878 → 6240 字符、03-review 4634 → 4709、SKILL.md 版本行 2.7.27 → 2.7.28。原件备份在 `C:\deepseek\study\work\_tmp\patched\`。

## 2.7.27 — 2026-11-22 · 跟上 html-card 的三条通道改动

`html-card` 今天改成「三个渲染器（VCP / `render_visual` / `a2ui`）加一个出口（`personalized-pages`）」，本技能有两处引用它的载体选路，逐处核对后改：

- **教学载体表缺 `a2ui`**：`02-lesson.md` 那张「讲什么 / 用什么 / 怎么落地」的表只有手写 SVG、`render_visual`、Mermaid、matplotlib、`univer_*` 五档，没有「一堆可比数据」的位置——成绩趋势、错题分布、章节进度对比、参数扫描这类，以前只能手写 SVG 硬画。补一行走 `a2ui`（声明式 JSON + 26 个受控组件，本地悬停与排序），并写明判据：**三个以上系列才值得**，两个数直接写在正文，别为两个数开一张图表。
- **`10-cards.md` 只讲了 VCP 一条路**：这一篇教的是讲解型卡（装帧、跟正文长在一起），走 VCP 没错；但没告诉读者「什么情况下不该走 VCP」。开头补一段分诊：只摆一堆可比数据时用 `a2ui`，四条通道怎么选见 `html-card` 技能，本篇不重复。

回归：`02-lesson.md` 5726 → 5878 字符（104 → 105 行）、`10-cards.md` 1376 → 1557 字符（42 → 45 行）；改动前原件备份在 `C:\deepseek\study\work\_tmp\patched\`（`*.bak-20261122-115631`）。

另：`skill-authoring` 里举本技能体系为例的那句「判据型示例：`html-card`（判据 / 两套渲染器边界 / 发卡前自检清单）」——「两套渲染器边界」这个词组在 html-card 里已不存在（节名改成「前两条通道的细节边界」），已改成「三个渲染器与一个出口的选路」。

## 2.7.26 — 2026-11-22 · 从八个同类技能里搬来两条教学法判据

读了插件自带的 7 个 `study-*`（study-book / study-tutor / study-guide / study-self / study-custom / study-companion / study-import）与 `good-learning`，共 409 行，逐条对照本技能原文核实「是否已有」。结论：真正可移植的只有两条——其余要么已有（「（资料以外）」标注、「AI 撰写 · 未核对」、「模拟」作答标注、全书不当出题证据、动手任务三律、双版排版、出新题先征同意、一次 5–8 题），要么是围着 StudyHub 应用转的契约（`study.scene.get` 读当前卡点、出完题回右侧工作台做、`started/waiting/recorded/done` 四桶、`course.book.revert` 回退），搬不过来。

- **练习没有难度梯度**（取自 `good-learning` 的练习四步梯度）：`02-lesson.md` 收题六问之后新增「一组题的梯度」四层表——完整例题（每步写理由，不写「易得」「显然」）→ 同构填步（挖判断步，不挖抄写步）→ 独立变式（题面写明改了什么条件，答案点出原解法哪一步在这里不成立）→ 混合回顾（至少掺两道两周前的题，专考「该用哪个方法」）。层数按章内容定，不够只出前两层、**不许跳层**；判据是「学习者能看出难度在爬坡，看不出就是四道并列的散题」。此前 `梯度` / `填步` / `变式` / `混合回顾` 四词全库 0 命中。
- **产出只验收了题干自足，没验收整份文件自足**（取自 `good-learning` 的自足性要求）：`06-output.md` 的「交付前必须真渲染」之后新增三条判据——前置在文内（用到的上节结论给一句回顾或指到 `第NN章_总结.pdf` 的哪节，不写「前面讲过」「如上节」）、例题与练习配套（答案册独立成立、一步一行带验算）、不指外部（不写「见教材 §5.3」「参考某网页」，要引原文就抄进来并标页码）。判据：单独发给一个没上过这课的人，他卡在哪一处，那一处就是不自足。
- 回归：`02-lesson.md` 5313 → 5726 字符（93 → 104 行）、`06-output.md` 7980 → 8341 字符（180 → 188 行），两处插入点复核过缩进与渲染；改动前原件备份在 `C:\deepseek\study\work\_tmp\patched\`。

## 2.7.25 — 2026-11-21 · skill-authoring 自足性验收修的 5 条

- **周复盘五步没有验收判据、也不说落在哪个文件**：`03-review.md` §四 每步补「**验收**＝…」，写明复盘记录落在 `<课程目录>\进度.md` 的「## 复盘记录」表；第 5 步补「顺手跑 `qbank.py errors --course <课程> --since <本周一>` 出本周错题本」——此前 `06-output.md` 把错题本列为周复盘产出，而这一节一字未提。
- **`qbank.py` 加 `--since`**（`stats` 与 `errors` 都有）：周复盘要「数本周对错」，但两个命令此前只能看全历史，只能手工过滤 `作答.jsonl` 的 `ts`。顽固题仍按全历史判；`errors --since` 只导本期内作答过的题。实测 `stats --course 傅里叶变换 --since 2026-11-15` 正常。
- **`progress-template.md` 要求填会话码，技能却没给生成规则**：§四 末尾补「按 `~/.dsh/AGENTS.md` 第 9 节 `<用途前缀>-<SHA1(sessionID) 前 8 位>-<后 4 位>` 全大写、不跨会话沿用」。
- **`kb.cmd` 在多处当命令直接用，却没说明它是使用者自配的**：`07-environment.md` 的「看资料原文」行与 `06-output.md` 引原句那条各补一句「没配就按 `04-kb.md` 第七节用 SQL 查」。
- **description 自相矛盾**：触发词写「把新教材/课件弄进来」，边界又写「不用于课件整理入库（见 study-intake）」。改成「把教材接进知识库」与「课件整理成册入库（拍照 / PPT / 扫描件转 PDF 那一步见 study-intake）」。
- 回归：`qbank.py` `py_compile` 通过，`stats --help` / `errors --help` 都有 `--since`，实跑 exit 0；SKILL.md 143 行 / 6751 字符，10 篇 references 与 9 个脚本引用零悬空。

## 2.7.24 — 2026-11-21 · 补上署名

- frontmatter 加 `author: "ZQY · LB-5E831608-0962"`（署名规则：`ZQY` + 写它的会话识别码，不写 agent 名）：`skill-authoring` 第 12 节要求「只给自己写的技能署名」，这个技能是会话 LB-5E831608-0962 写的，之前一直空着。
- 同批给 `study-intake` 补了同样的署名。
- 其余字段不变；`version` 仍不写进 frontmatter（加载器不读，见 2.7.23 那条）。

## 2.7.23 — 2026-11-19 · 两份审查回来的 19 处

- **顽固题名单两份对不上（最重）**：`cmd_errors` 在「已解除」判断之后还多一句「最后一次做对就跳过」，于是「错错错对」的题在 `stats` 里算顽固、在错题本里不出现。删掉那句，判据只剩 `count_failures` 一处。
- **错题本不带题号**：md 里只有题干，回头要用 `qbank.py grade` 复刷时找不到 `q-xxxx`。现在每题第一行是「题号：`q-xxxx`」，selftest 也加了断言。
- **`render_quiz_pdf.py` 四类静默通过**：`--answers` 与题卷／源文件同名会互相覆盖（rc 仍 0）；答案节只有标题会生成空答案册；只有 `# 标题` 的 md 会生成空卷；`--blank` 负数会被写成负高度的 rule。现在五处都先查再写，错了给中文原因和改法。
- **`render_study_pdf.py` 的 map-config 报错**：nodes 不是 6 个时抛裸 `ValueError`，缺键抛裸 `KeyError`，不传时说成「文件里没有该 kind」。改成中文报错，带 kind、实际个数、以及该改哪个字段。
- **文档 12 处**：selftest 步数（三处）；README 结构树补 `10-cards.md`；XeLaTeX 从「软」档单列成「出 PDF」档（它没有降级路径）；`06-output.md` 的 `--blank` 示例补 `--course`；目录树里 `产出\_old\` 纠正成 `_old\`；`06-output.md` 内部两处页数口径统一（封面与地图是同一页）；「地图」不再当成一种 kind；「每题 ≥3 cm」的方位词改成「上面」；`07-environment.md` 的「插件提供的工具」改成「本地脚本与会话工具」；`01-start.md` 的讲义落点补 `产出\` 一层；`03-review.md` 与 `08-sharing.md` 的「与插件同源」统一成「与 ts-fsrs 标准实现」。
- 回归：selftest 26 步全过 · 13.5s；doc_check 12 篇 / 9 脚本 / 161 处参数引用全部对上（196 处命中）。

## 2.7.22 — 2026-11-19 · 三处小修：角标、姓名栏、节号

- **路线图左上角标默认「备考路径」→「学习路线」**（`render_study_pdf.py:250`）：非应试的课（比如只想把一门课学完）不该被默认贴上应试标签，此前每一份都得靠 `--map-config` 里的 `caption` 手动盖掉。
- **答案册不再印「姓名／学号／日期」**：`build()` 之前无论题卷还是答案册都调 `\quizhead`（三栏填名用的），而专给答案册写的 `\answerhead` 定义了却从没被调用过——死宏。现已接上，并去掉它开头的 `\clearpage`（答案本来就在独立文件里，不需要清页）。
- **`04-kb.md` 第七节的「回去看第五节」改成第六节**：现在这篇有八节，验收判据对不上时要回的是「用脚本建」那节。这类章节交叉引用 `doc_check` 管不到（它只验参数名），只能靠人工核。
- 回归：selftest 25 步全过 · 13.1s；doc_check 全部对上（193 处命中）。

## 2.7.21 — 2026-11-19 · 总结要写实，页数不为内容让路

- 用户两条：「产出的 PDF 优先保证质量，页数没必要过度压缩」「总总结的总结部分是不是太简洁了」。
- 上一版为了把总总结压回两页，删掉了那句点睛的「整门课只做一件事」，还把结尾压成两行口号——本末倒置：产物是给人看的，页数不是指标。
- `06-output.md` 改两处：①末尾那节「总结」**要有实质内容**，把全课收成一条线（傅里叶级数＝换一组正交基、系数＝投影；级数到变换＝周期放到无穷），说清哪几件事是同一件事，再给学完的标准，只复述条目等于没总结；②**页数不为内容让路**——正文约一页、多了就自然翻到第 3 页，不要为压页数删内容。
- 同日总总结重出：3 页（地图 1 + 正文 2），「五、总结」四段写实（换基、投影、级数到变换的两次加强、地基为什么笨但必要）。
- 回归：selftest 25 步全过 · 13.6s；doc_check 全部对上（193 处命中）。

## 2.7.20 — 2026-11-19 · 答案挤成一块，总总结写成了流程

- 用户两条反馈：答案「一步一行并且带小标号」、总总结「不像给我看的，像给你看的」。
- 答案连排的真因：`render_quiz_pdf.py` 的 `body_tex` 只在 question / ordered 分支写 `\par\noindent`，普通段落 `flush()` 只 append 行内文本，空行分隔的几段到 LaTeX 里就连成一段——逐步写的答案渲染出来是一整块。修法：`flush()` 改成 `\par\noindent` 开头。
- `06-output.md` 补两条体例：**答案册一步一行带（1）（2）（3）（4），（4）验算不能省**，md 里每步之间空一行；**总总结写知识不写流程**——讲数、每讲节奏、回测点、周次归 `进度.md`，总总结只写「讲什么 / 主线公式 / 每阶段结论 / 常错处 / 学会的标准」，正文约一页，`--layout compact` 对它不起作用。
- 给验证工具补洞：`selftest.py` 加「render quiz（答案分段）」断言（答案 md 的三段该排成三段），24 → 25 步。
- 回归：selftest 25 步全过 · 13.5s；doc_check 12 篇文档 / 9 个脚本 / 158 处参数引用全部对上（193 处命中）。

## 2.7.19 — 2026-11-19 · 卷面漏进一行 markdown 井号

出第一份阶段测试卷时发现的：**PDF 卷面上多了一行 `# 傅里叶变换 · 阶段 1 测试卷`**，带着井号一起印了出来。

- **原因**：`render_quiz_pdf.py` 的 `HEADING` 正则只匹配 2–3 个 `#`（`##` 章节标题），md 第一行的一级标题既不匹配标题、也不匹配题目，落进 `paragraph` 分支被当正文渲染，而 `inline()` 又不处理 `#`。
- **改法**：新增 `DOC_TITLE = ^#\s+\S`，命中就跳过——卷头已经由 `--course` / `--lesson` 呈现了课程与讲次，源文件的一级标题纯属重复。模块 docstring 的 Markdown contract 也补了这一行。
- **顺带给验证工具补洞**：`selftest` 原本只在题卷里断言「不含答案文本」，没人检查「卷面出现了不该有的字」。新增 `render quiz（文档标题不进正文）`（23 步 → 24 步），拿 `QUIZ_MD` 第一行的「随堂卷」做哨兵。

回归：`selftest` 24 步 24 OK · 13.3s；`doc_check` 12 篇文档 · 9 个脚本 · 参数引用全部对上。

## 2.7.18 — 2026-11-19 · 出题不标章节，三条统计静默瘫掉

演练步 7/8/9 时撞上的：五道题全落进「(未标知识点)」。

- **`add` 的示例漏了 `--chapter` / `--topic`**：`qbank.py add` 本来就有这两个参数，但 `02-lesson.md` 速查表那一行只写 `--prompt / --answer / --source`，正文的入库说明也没提。于是加题一律不标章节，而**不标不报错**，只是三件事同时退化：`stats` 的「错得最多」变成一坨「(未标知识点)」、错题本没法按章分组、`pick --chapter` 一道也抽不出来（实测 rc=1）。
- **改法**：速查表的 `add` 行补齐 `--chapter` / `--topic`；正文入库说明写明「必须带，不标就静默失效」并列出三个后果；第 4 步的顺序锁死句也补上这两个参数。
- **顺带给验证工具补洞**：`selftest` 第 2 步一直在传 `--chapter`，但**没有一条用例验证「按章抽得到」**——参数存在、题也带章节，链路照样可能断而测试全绿。新增 `pick --chapter 按章抽题`（22 步 → 23 步）。

回归：`selftest` 23 步 23 OK；`doc_check` 12 篇文档 · 9 个脚本 · 参数引用全部对上。

## 2.7.17 — 2026-11-19 · 去 StudyHub 时漏掉的第五步

跑完整十步法时撞上的：**步 5「写全书」指向的技能不存在**。

- **步 5 还写着 `study-book`**：十步法表那一行是「每个知识点写一节 | `study-book` | 复习全书」，而 `study-book` 是 StudyHub 插件的技能（全部动作走 `study_workspace` 的 `book.toc` / `book.read` / `book.write`）。2.7.12 去依赖时的终检清单里没有这个词——当时 grep 的是 `StudyHub|studyhub|study_workspace|study.session|branch\.|card\.grade|review\.start|qbank_import|export_studyhub`，漏掉的正是「技能名」这一类。全目录只有这一处命中，但它正好是步 5 唯一的路，等于这一整步在去掉插件后**没有落点**。
- **改法**：步 5 由本会话直接写文件到 `学习进度\<课程名>\复习全书\第NN章.md`；`06-output.md` 新增第六节，给出这一节的结构（为什么 → 公式 → 一步一算的例子 → 常见陷阱 → 在地图上的位置）与四条硬规则：引教材原句必须真打开过那一页、自己补的类比紧跟「（资料以外）」、全书不当判分依据也不当出题证据、文件顶上标库内页码。复习全书放在 `产出\` 之外——它是底稿不是成品。
- **顺带修**：`06-output.md` 目录示例里 `产出\_old\` 的错缩进（照抄会建出一个 `产出\产出\_old\` 这样的目录）。

回归：`selftest` 22 步 22 OK · 13.5s；`doc_check` 12 篇文档 · 9 个脚本 · 149 处参数引用全部对上（184 处命中）。

## 2.7.16 — 2026-11-19 · 真跑一轮抓到的五处：有要求没动作

这一版不是脚本 BUG，是**文档写了「要做什么」、没写「在什么时候、用什么动作去做」**。跑了一整轮真课（傅里叶变换，摸底到第一讲）才暴露——前四轮只测脚本层，流程层从没被验证过。

- **卡片交付零规范（最重）**：28 个文件 254 KB 里没有一处讲卡片怎么做，而讲解几乎全靠会话里的卡片承载。真跑里三次翻车全靠学习者截图指出：浅底被深色主题覆盖成黑底黑字；含 `font-family` 的规则被渲染层重写、同一条规则里的 `color` 一起丢了，表现成「只有标题变黑字、正文正常」；正文字号 12.5px 连被说「小」两次。新建 `references/10-cards.md`：根容器背景与字色都写行内 `!important`、不用 `<style>` 块、只用系统字体、字号下限一张表（正文 17 / 标题 26 / 材料 15）、浅底配色定稿、交付前三条自检。
- **「讲完一讲就改进度表」没有落点**：`02-lesson.md` 第 7 步与 `03-review.md` 第一节都写了「每讲结束只改一行」，但没说什么动作、什么时机。改成硬顺序——**发下一条回复之前改完**：状态从「未讲」改「讲完」、「对 / 错」填实际数字、「更新」列写当天与会话码；漏了就在下一讲开场先说「上一讲的记录我漏了，先补上」，不默默跳过。
- **出题与入库的顺序没锁死**：第 4 步说「同一道题同时进本地题库」，没说先哪个。实测讲完只出了题、没入库，两轮之后才发现题库还是空的。改成**先 `qbank.py add` 拿到 q-xxxx，再抄进正文**。
- **「记忆里交代过的直接沿用」没给查询动作**：`01-start.md` 第 22 行有这条纪律，全文没有查记忆的命令。结果白出一套七题——同一学科十六天前他答过一模一样的先修诊断。补上 `memory_search` 与 `memory_project` 两条命令，并要求查到后当场念一遍确认「现在还是这样吗」。
- **「资料可用性当场核一遍」顺序反了**：原第 23 行只说核一遍，没说在问之前。真跑里他答「什么都没有」，库里躺着两本对口教材，差点按零底座排完整条路线。改成**先 `kb.cmd find "<课程核心词>"` 看库里的，再拿结果问缺哪一段**；第 3 问的「决定什么」列也写明「先查库再问」。

回归：`selftest` 22 步 22 OK · 12.7s；`doc_check` 12 篇文档（新增一篇）· 9 个脚本 · 149 处参数引用全部对上（184 处命中，比 2.7.15 多 2 处）。技能从 28 文件 254 KB 长到 29 文件 261 KB。

## 2.7.15 — 2026-11-19 · 去重与行为对齐：8 处

这一版修的都不是「写错了」，而是**同一件事有两个落点**——两处各写一半，改一处漏一处。前四轮的 19 处里有一半是这类长出来的。

- **顽固题解除条件：文档与代码差两个数量级**（行为级，最重）：`03-review.md` 写「最近连续 3 次全对自动解除」，代码 `recent = mine[-5:]` + `all(correct)` 要最近 **5 条全对**——最近 3 次全对但 5 条里有过一次错，就永远解除不了，学习者的错题本只会越堆越长。改成真按最近 3 次判。
- **`stats` 与 `errors` 两套 ★ 判据**：前者用「累计失败 ≥3 **或** 最近 5 次错 ≥60%」，后者只有「累计失败 ≥3」——「3 次作答 2 次错」在统计里算顽固题、在错题本里不标 ★。判据收进 `count_failures()` 一处定义（返回 `fails/rate/recent/cleared/stubborn`），两个命令都调它。
- **`06-output.md` 承诺 `## 第 N 章` 换页，代码只认 `## 单元 N`**：`render_study_pdf.py:177` 的正则只匹配 `单元\s*\d`，`## 第 N 章` 落到通用 level-2 分支——只渲成章节名、静默不换页，学习者拿到的是连排的一坨。正则补上 `第\s*[0-9一二三四五六七八九十百]+\s*章`。
- **`05-materials.md` 让读者去用 `kb.py` 建库，而技能只带 `build_kb.py`**：本机有 `_kb\app\kb.py` 所以从没暴露，分享出去的人会找一个不存在的建库器。改成「建库用 `scripts/build_kb.py`；`kb.py` / `kb.cmd` 是使用者自己配的查询 CLI，技能不附带」，并在 `04-kb.md` 第六节写明「别把查询 CLI 当建库器用——它不做抽取，也不建 FTS」。
- **`01-start.md` 第五节是第三节的复述**：同一个课程档案，第三节讲「怎么建」、第五节又讲一遍「长什么样」。第五节删掉，进度表判据并进第三节第 1 步。
- **`03-review.md` 第七节是第六节的复述**：`## 六、出题与复习` 已说 pick/due/stats/errors，`## 七、题库与复习` 又说一遍，只多一条 `exam --date`。第七节删掉，exam 并进第六节。
- **孤儿编号「4.5」**：`01-start.md` 标题写 `## 三、4.5 把路线落成课程`，可全篇没有第 4.5 节，`SKILL.md` 两处照抄「用 4.5 建课」。标题改成「第三节」，两处引用跟着改。
- **`SKILL.md` 自认的「两套怎么学」判错了对象**：原文说知识点清单八项与阶段表打架，其实清单只在 `06-output.md` 定义、`01-start.md` 只是指针。真打架的是 `06-output.md` 的六项学习计划与 `01-start.md` 的四项阶段表——同一份计划两套阶段数（一个「1–12（通常 3–5）」一个只写「3–5」）。改成「阶段划分以 01 为准，06 只是补足成排版内容」，并在 06 的六项计划后写上这句。顺手把「产出六件套」改成「产出六件（六份文件 + 随堂小题）」——那张表实际有 7 行。

回归：`selftest` 22 步 22 OK · 12.6s；`doc_check` 11 篇文档 · 9 个脚本 · 148 处参数引用全部对上（182 处命中，比 2.7.14 多 1 处是新增的 `qbank.py exam` 引用）。顽固题三口径实测：错错对对对 → 已解除、不算顽固；错错错 → 顽固；错对错（67%）→ 顽固，且 `stats` 与 `errors` 名单完全一致。

## 2.7.14 — 2026-11-19 · 第四轮 BUG 测试：19 处

- **`--date` 一调就崩**（最重）：2.7.11 给它加了 `type=iso_date`，函数里却还留着 `date.fromisoformat(args.date)`——argparse 交进来的已是 `date` 对象，三者一律 `TypeError: fromisoformat: argument must be str`，`exam --date` / `pick --date` / `due --date` 全部 rc=1；文档 `03-review.md:120`、`07-environment.md:108`、`09-local-store.md:75` 照抄即挂。删掉重复解析，`exam` 存盘改 `args.date.isoformat()`。
- **`doc_check.py` 扫不到反斜杠续行**：只按行扫，`qbank.py add --course demo \` 换行写的参数完全没进检查，「全部对上」不代表能跑；现在先合并逻辑行再匹配（命中数 173 → 181）。
- **`selftest.py` 覆盖不到 exam**：19 步里没有一条带 `--date`，所以上面那个崩溃能全套通过。加 `exam 设考试日` / `exam 读回` / `pick --date` 三步（19 → 22 步），并把临时目录清理挂到 `atexit`，中途抛异常也不再留 `studyflow-temp-*`。
- **脚本表少一半**：`07-environment.md` 六节的脚本表只列 6 个，补上 `qbank.py`、`doc_check.py`、`selftest.py`。
- **`STUDY_KB_DB` 已成死配置**：它唯一的读者 `export_studyhub_md.py` 在 2.7.12 删了，`07-environment.md` 两处仍把它当覆盖口，读者会配一个没人读的环境变量；删掉，只留 `QBANK_PROGRESS`。
- **`source.search` 两处残留**：`07-environment.md` 的 kb 降级行与 `check_env.py` 的提示仍写 `doc_text / source.search`，改成 `doc_render`。
- **文档里还留着插件期动作**：`02-lesson.md` 的「不推右侧」「不要求他去右侧」「`card.get` 取 rubric」「`explicitUserAuthorization: true`」四处；`SKILL.md` 步 4 的落点写 `sourceIds`；`SKILL.md` 对 09 的描述还提「迁移（从插件搬题）」——该节已删。全部换成本地说法。
- **`01-start.md` 开课五步三处不通**：第 1 步就拷模板到 `学习进度\<课程名>\`，可那个目录要第 4 步 `qbank.py init` 才建；开头说「三份文件全部写盘」而第 3 步又说「说可以才写盘」；「三份」也没说清是哪三份、`能力评价.md` 全程没有创建动作。改成「三样东西 + 步 1–2 先在草稿、确认后一并落盘 + 目录不存在先建」。
- **`05-materials.md` 命令块用 `--` 当注释**：Windows 命令行里 `--` 不是注释，整行照抄会把说明当参数传进去；说明移到命令块外。
- **`job.wait` 两处孤儿**：`03-review.md:111` 与 `07-environment.md:93` 仍把 `job.wait` 当「等出题结果」——出题与判分现在都是同步的 `qbank.py` 命令，没有后台任务可等。
- **`doc_check.py` 的计数口径写进输出**：只统计同一逻辑行、脚本名之后的 `--flag`，且只验参数名、不验必填——绿了也不代表命令能跑。

## 2.7.13 — 2026-11-19 · 修三处照抄会失败的命令

- **两处示例命令缺必填参数**：`references/03-review.md` 的 `qbank.py pick --n 3` 与 `references/07-environment.md` 的 `qbank.py export --out 题库.md` 都漏了 `--course`，照抄会 `error: the following arguments are required: --course`（rc=2）；已补成 `--course <课程>` / `--course X`。
- **首课出题顺序反了**：`references/01-start.md` 原来把「从题库取」排在「本会话自出」前面，但新开课时题库必空、`qbank.py pick` 返回退出码 1 并打印「没有可抽的题」——那是正常状态不是出错。改成首批题本会话自出，之后每次课才从到期题里取。
- **判据留给后来人**：行文里写命令名可以简写（`qbank.py due`），但凡写成「可照抄的一行」就必须带齐必填参数；`doc_check.py` 只验参数名存在、不验必填性，这一条靠人。

## 2.7.12 — 2026-11-19 · 去掉对 StudyHub 的依赖

- **主路径换成本地**：`01-start.md` 第三节从「插件落课 + 生成草稿 + publish」改成「写课程档案 → 建题库 → 第一批题入库」，课程档案 `学习进度\<课程名>\进度.md` 新增「## 路线」阶段表（阶段名 / 活动 / 讲数 / 什么算过四项），`assets/progress-template.md` 同步加了这一节与两行示例。
- **删插件动作**：`02-lesson.md` 七处、`03-review.md` 两处里只剩插件才有的步骤（`study.session.start/resume/pause/end`、`study.scene.get`、`study.question.prepare/result`、`branch.open/return`、`review.start/reveal`、`card.grade`）全部换成本地说法或删除；「题目与作答只存本地一处」成为唯一口径。
- **材料入库改验收**：`05-materials.md` 第四节从「送进 StudyHub」换成「材料就位后的验收」——三条命令 `kb.cmd find` / `kb.cmd page` / `kb.cmd status` 与判据（挑三个词都能命中、点开的页对得上、页码偏一章以上说明基准没对齐）。
- **删脚本**：`scripts/qbank_import.py`（StudyHub 题组一次性迁移）、`scripts/export_studyhub_md.py`（把库导出给插件当材料）——依赖没有了，留着只会误导。
- **去掉旁注**：`SKILL.md` / `README.md` / `01`–`09` 里「装了 StudyHub 就多一个资料库与面板」这类限定语全部删除；`09-local-store.md` 删掉「从 StudyHub 迁出」整节并把后两节节号顺延（六→五、七→六）；`qbank.py` docstring 与 FSRS 口径里的「与 StudyHub 那份 ts-fsrs 移植」统一改成「与 ts-fsrs 标准实现」，「照 StudyHub 的四类排除」改成「四种不计入的作答类型」。
- **依赖自检**：`check_env.py` 不再报 StudyHub 一项（脚本本来就测不到它，报着只会让人以为缺了什么）。
- 结果：除本文历史段外，技能目录零 `StudyHub` 字样；能力面不变——建课、讲、练、复习、材料检索、出 PDF 全部走本地文件与 `qbank.py`。

## 2.7.11

- **`restore` 改成原子操作**：原来「先删旧文件再解压」——中途遇到只读文件或坏 CRC，就留下半恢复的目录（实测只读排期 → 题库与作答已被删；坏 CRC → 题库被换成 0 字节）。现在先解到暂存目录校验，全部成功才转存旧文件、整体替换；失败时原文件一个都不动，并给「原文件没动」的提示。
- **`restore` 校验备份归属**：读 `_meta.json` 的 `course`，与 `--course` 不一致时拒绝（实测拿 A 课备份恢复到 B 课目录会静默混课），提示怎么改。
- **坏排期不再崩**：`due` / `pick` 原来直接 `s["due"]` 与 `date.fromisoformat(...)`，排期里一条缺 `due` 就抛 `KeyError` / `ValueError` 裸回溯；现在统一跳过并计数打印「排期里有 N 条缺 due 或格式不对」，`pick` 把这类题当新题。
- **日期与题数走 argparse 校验**：`exam` / `pick` / `due` 的 `--date` 改成 `iso_date`（`2026-02-30` 这类报「要 YYYY-MM-DD 的真实日期」rc=2，不再抛 `ValueError`）；`pick --n` 改 `positive_int`（原来 `--n -1` 静默少抽、`--n 0` 静默空跑）。
- **`check_env` 挡类型错误**：`texlive_bin` / `kb.db` 不是字符串时报一行 NO 继续，不再 `TypeError: argument should be a str or an os.PathLike object`。
- **`errors` 补第四态**：这门课一次作答都没有时明说「还没有任何作答记录」，不再并入「错过的都做对了」制造假成功。
- **`compile_study_pdf` 跳过绝对路径图**：`\includegraphics{C:/...}` 原来会 `SameFileError` 编译失败，现在直接跳过（文件本来就在原地）。

## 2.7.10

- **文档契约对齐**：`07-environment.md` 的退出码说明改对——只有必需项失败才为 1，可选包的 `--`（如 `py: fitz`）不影响退出码（实测 `check_env.py` 对 fitz 缺失仍返回 0）。
- **命令补必填参数**：`02-lesson.md` 的题库命令表 `pick` / `add` / `grade` / `due` 全补上 `--course`（`grade` 补 `--qid`）——原来照抄必报 `the following arguments are required: --course`。
- **口径纠正 8 处**：`02` 删掉「任务类写回面板用 `card.grade`」（与「题目作答不放插件」冲突）；`01` 零底座建目录不再把题库画进课件目录；`03` 放水阈值补样本量（≥4 次按 25%、2–3 次按 50%，与代码一致）、开头三张表补全「复盘记录」；`09` 路径图改 `<progress_dir>\<课程名>\`（progress_dir 为绝对路径时原来写错）、迁移示例占位符改 `<study_dir>`、`ease` 不再声称会换算（代码只认 `interval`）；`06` 的 `knowledge` / `plan` 说明补上「兼作章节总结 / 总总结」。

## 2.7.9

- **并发写数据安全**：`qbank.py` 原文在 Windows 上两个进程同时追加会互相覆盖写指针——实测两个进程各加 5 题只落下 7 行、`qid` 还撞号。新增 `file_lock()`（`<文件>.lock` 独占 + 10 秒重试），`add` / `grade` / `backup` / `restore` 四个写命令的「读-改-写」全部关进临界区。
- **排期原子写**：`save_schedule()` 改成写临时文件再 `os.replace`，写到一半崩了也不会留半截排期把复习进度带坏。
- **只读文件友好报错**：题库被设成只读、或被别的程序占着时，`append_jsonl()` 与 `save_schedule()` 打印「写不了 X：…关掉打开它的编辑器再试」，不再抛 `PermissionError` 的裸 traceback。

## 2.7.8

第二轮脚本审查（11 条，全部实测复现后修）——多半是「安静出错」类：不报错，但结果不对。

- **数据安全三处**：`init.py` 原来先写 `config.json` 再建目录，目录建失败就留下半配置、重跑还被「已存在」挡住（现在先建目录，失败不落盘）；`qbank.py errors` 默认写 `错题本.md` 是无条件覆盖，学习者补的笔记会静默消失（现在旧版先转存进 `backup\错题本-<时间>.md`）；`qbank.py restore` 改成整课替换语义，恢复前把现存五类文件整体转存（原来只覆盖 zip 里有的，会留下「新题库 + 旧作答」的混合状态）。
- **口径对齐两处**：`backup` 允许只备份到进度/评价（原来 rc=0 却永远恢复不了），现在缺题库时明确警告；`restore` 不再硬要求 `题库.jsonl`，任一课程文件即可，只拒「什么都没有」的包。
- **安静出错四处**：`check_env.py` 用 `if cfg:` 做闸门，空 config 时全部检查跳过还报「必备项齐」；config 里 `study_dir: 123`、`kb: "enabled"` 直接抛 traceback；`qbank.py stats` 遇到排期缺 `due` 整体崩（现在跳过并告警）；`qbank.py errors --limit -1` 会切掉题目还写出空的错题本（现在负数直接拒）。
- **假阳性两处**：`doc_check.py` 的资源引用正则只认 `assets\<文件>` 一层，`assets/demo/demo-material.md` 完全不进检查却报「全部对上」；`compile_study_pdf.py` 只复制固定目录名（figures/images/img…），`\includegraphics{sub/fig.png}` 这类任意子目录的图会丢（现在按 tex 里的引用逐条带过去）。
- **文案一处**：`qbank.py errors` 结果为空时把「作答全被排除」说成「都做对了」，现在区分题库空 / 全被排除 / 确实做对。

## 2.7.7

第二轮 BUG 审（子代理 12 条全部核实成立）后的修补。

- **代码两处**：`qbank_import.py` 读的是 `scripts\config.json` 而 `init.py` 写在技能根目录 → 新装环境跑迁移示例必报「先跑 init.py」，改成读技能根；`check_env.py` 的 xelatex 缺失原来只标 `--` 不进 `required_fail`，与「XeLaTeX 是硬依赖」口径不符，现在退出码 1。
- **文档十二处**：`02-lesson.md` 的「三段一步不能省」会让人对现成题也 `add`（重复题入库）；`03-review.md` 仍教往插件题组写题、复习仍写 `review.start`；`06-output.md` 自相矛盾三处（四种 kind 都带封面地图 / 留白归 quiz / 标题指令不限 kind）、「退成 md 一屏」是 2.7.4 已撤的降级残留；`README.md` 三问里还有「编译器在哪」、文件表仍写「PDF 与 Markdown」；`09-local-store.md` 交叉引用指错节；`assets/map-config.example.json` 仍写「题组存一份」。

## 2.7.6

边界实测修两处：`errors` 的 `--out` 与文档对不上、`restore` 撞坏 zip 直接抛 traceback。

- **`qbank.py errors --out` 改成可选**（默认 `<课程目录>\错题本.md`）：原来它 `required=True`，而 `06-output.md`、`03-review.md` 里写的都是不带 `--out` 的 `qbank.py errors`——照文档敲会直接报「arguments are required: --out」。
- **`qbank.py restore` 补坏 zip 处理**：截断或非 zip 时原来抛 `zipfile.BadZipFile` 裸回溯（exit 1），现在给「这不是有效的 zip（可能没下载全，或被截断）」并 exit 2，与「没有题库」「越界路径」两条拒绝口径一致。

## 2.7.5

补一条「装过也会消失」的坑：DSH 运行时升级会重置 site-packages，`pypdfium2` / `pypdf` 会静默不见（本机 `cv2` 已因此丢过两次）。原来的文档只说「没装怎么办」，盖不住这种情况。

- **`check_env.py`**：`py: pypdfium2` / `py: pypdf` 缺失时的提示从「未装（材料线受限）」改成「未装或已被运行时升级重置——重装：`python -m pip install pypdfium2 pypdf`」；`fitz` 单独标「可选，不影响主链」。
- **`07-environment.md`**：系统层表那一行点明「装过也会消失」；装法段补「装完不是一劳永逸」——库文件与数据不受影响，重装即可。

## 2.7.4

撤掉「没有 TeX 就出 Markdown」这条降级路径——公式排不出来，md / HTML 顶替的产物没有价值。改成入口校验、说清后果。

- **`init.py` 校验编译器**：`--texlive-bin` 指向的目录里没有 `xelatex` 直接报错退出（exit 2）；自动探测失败时 config 照写，但收尾打醒目提示——建课不受影响，出不了 PDF，并给出装完重跑的命令与 `texlive_bin` 填法。
- **文档口径统一**（`06-output.md` / `07-environment.md` / `08-sharing.md` / `README.md`）：XeLaTeX 从「可选（出 PDF）」改成「只要出产物就必需」，缺了**没有降级替代**，停在出产物这一步先装 TeX；`07-environment.md` 第三节开头单独点明这是唯一没有降级路径的依赖。
- `check_env.py` 与 `compile_study_pdf.py` 的提示同步改成「出不了 PDF，先装 TeX」，不再暗示可以降级成 Markdown。

## 2.7.3

补两个「跑一学期才会疼」的缺口：自评与客观对账、整课打包。

- **`qbank.py stats` 增加自评对账**：算出「自评 good/easy 占比 vs 客观正确率」，偏差过大直接给判词——`good/easy ≥ 80%` 且正确率 `< 60%` 提示「评得偏松，下一轮把 good 压成 hard」；正确率比 `good/easy` 高出 15 个点以上提示「评得偏紧」。原来只有口径，要人自己算。
- **新增 `qbank.py backup` / `restore`**：`backup --course X` 把题库 / 作答 / 排期 / 进度 / 能力评价打成一个 zip，带 `_meta.json` 记题数与作答数，默认落 `<课程>\backup\<课程>-时间.zip`；`restore --course X --src 备份.zip` 恢复，覆盖前把旧文件存进 `backup\pre-restore-时间\`，并拒收没有 `题库.jsonl` 的 zip 和带越界路径的 zip。

## 2.7.2

把两件「每次都要现写临时脚本」的事固化成脚本，并补三处手感（产物与 kind 的对应、自评校准、错题本）。

- **新增 `scripts/selftest.py`**：19 步端到端自检，临时目录 + `QBANK_PROGRESS` 改道，不碰真实数据；覆盖建课 → 加题 → 抽取 → 判分（含答错断步）→ 统计 → 到期 → 错题本 → 三种产物 → 编译 → 环境探测 → 两条负向（课程名打错要非 0、缺答案节要非 0 且不落盘）。约 13 秒；没有 xelatex 时编译步骤 SKIP 而非 FAIL。
- **新增 `scripts/doc_check.py`**：ast 静态解析 11 个脚本的 argparse，扫 11 篇文档里 `xxx.py --flag` 的引用，比对参数是否真存在、引用的 assets / references 文件是否存在、`map-config.example.json` 是否覆盖所有需要地图的 kind。零执行、只读。
- **`qbank.py errors`**：从 `作答.jsonl` 直接生错题本 md（顽固题标 ★、`--limit 0` 全出、`--with-answers` 附答案页、无错题不写空文件），再接 `render_study_pdf.py --kind errors` 出 PDF。不再手抄错题。
- **产物 → kind 实测表**（`06-output.md`）：`knowledge` 章节总结 3 页 / `plan` 总总结 2 页 / `day` 当天安排 8 页 / `errors` 错题纸无封面无地图。**速查册脚本造不出一页**——四种 kind 都带「封面 + 地图」两页固定开销，正文只写标题也是 2 页，`--layout` 不影响；要一页就手写 `.tex`。
- **FSRS 自评校准**（`03-review.md`）：四档判据钉成动作（`again` 说不出下一步 / `hard` 犹豫后对 / `good` 直接做完 / `easy` 秒答且换数仍对），并给对账口径——自评 good / easy 占八成以上而客观正确率不到六成即放水，下一轮把 good 压成 hard。
- 顺带修 `02-lesson.md` 一处参数写错：`qbank.py grade` 写成 `--id` / `--rating`（不存在），改为 `--qid` / `--grade`——由 `doc_check.py` 首跑抓到。

## 2.7.1

修 31 处 BUG（数据风险 4 / 文档不符 10 / 旧双后端残留 8 / 健壮性 6 / 小瑕疵 3），由两个只读审查员 + 逐条实测得出。

- **数据风险**：`qbank.py` 配置损坏与排期损坏不再静默吞掉（改为报错退出）、相对路径不再猜、删题后 id 不再撞；`build_kb.py` 同名 PDF 不再互相覆盖。
- **文档**：目录树里题库归位到 `学习进度\<课程名>\`、十步法编号消歧（「步 4」不再指两件事）、`--blank` 归属改到 `render_quiz_pdf.py`（单位 mm）、`export_studyhub_md.py` 说明改为按教材页段导出、配置键数 七→六、references 标题里的旧宿主编号括注去掉。
- **旧双后端残留清零**：`card.search` / `supplement` / `card.grade` / `study.session.*` 在正文里全部换成 `qbank.py pick/add/grade`，或明确标「装了 StudyHub 才有」。
- **健壮性**：`build_kb.py --list` 不再偷偷建空库；`qbank.py` 课程名打错直接报错并列出已有课程；`render_quiz_pdf.py` 缺答案节不再落半成品；公式闭合行带尾随文字不再读到 EOF；圆圈数字字体缺失有 `\IfFontExistsTF` 兜底；`compile_study_pdf.py` 编译时带上相对路径图片。
- `check_env.py` 支持 `--help` / `--json` / `--quiet`（原来无 argparse，`--help` 被忽略）。

## 2.7.0

- 开课补一问「范围」：整本 / 只第几章 / 只要某个专题，写进课程档案文件头；范围说不清先别排日期表。
- 产物加第六件「速查册」：一章一页，核心结论 + 公式符号 + 两条易错 + 例题索引。
- `06-output.md` 五件套改六件套，新增速查册格式与字号下限。

## 2.6.0

- **题库只留本地**：删掉 `config.json` 的 `store` 键与 `init.py --store` 参数（以及第四个问题），题目 / 作答 / 排期只走 `scripts/qbank.py`，没有第二个后端可切。
- `09-local-store.md` 标题与开头改写（从「不装 StudyHub 时」改成「题库、作答与排期」），删掉后端选择段；迁移段标明「历史一次性」。
- `02-lesson.md`、`03-review.md`、`07-environment.md`、`README.md`、`08-sharing.md`、`SKILL.md` 清掉「本地模式 / 装了 StudyHub / 两条路不混用」这类双后端措辞，StudyHub 统一降为「可选资料库与面板」。
- `03-review.md` 的题库操作段同步成 FSRS-6 四档（原文还写着「裁成两个参数」）。

## 2.5.0

- 题库后端默认改为本地：`init.py` 的 `--store` 默认 `local`、交互问句改成「本地（默认）/ studyhub」，`config.json` 只有想用 StudyHub 面板做题时才写 `studyhub`；`07-environment.md`、`README.md`、`08-sharing.md`、`09-local-store.md`、`SKILL.md` 铁律同步改为本地优先。
- `qbank.py` 新增收题检查：`add` 写入前自动查题干自足（无「如上图 / 由上可知」这类指代）、有答案、有出处、选项像样、不是重题；默认只打印提示，`--strict` 有提示就拒绝写入，`--no-check` 跳过。
- `qbank.py` 新增 `audit` 子命令：同一个检查批量跑全库，逐题列出提示，有提示时退出码 1。实测现有 27 题（固体 12 / 高量 15）0 提示。
- `09-local-store.md` 命令段补 `audit` 示例与「收题检查」小节（五条自动查 + 两条只能靠人）；`02-lesson.md` 的收题六问后补一句「哪几条是脚本查的」。

## 2.4.0

- 本地排期从「FSRS 式两参数」升级为完整 FSRS-6：难度 D 随作答更新（`D' = D − w6(g−3)(10−D)/9` 再向 D0(4) 均值回归 `w7`），答对分支补上 `e^w8` 与 hard / easy 乘子，首次 S、D 按档位取 `w[g−1]` 与 `D0(g)`。
- `qbank.py grade` 支持四档 `--grade again|hard|good|easy`；`--correct` / `--wrong` 保留为 good / again 的别名。作答记录新增 `grade` 字段，统计与打印按档位显示。
- `09-local-store.md` 第四节整段改写：四档表、S/D 双状态公式、难度更新式，以及与 StudyHub 的差异说明改成「只差短期步骤与随机抖动」。
- `02-lesson.md` 随堂题批语与带学动作表、`03-review.md` 判分口径、`SKILL.md` 禁区、`README.md` 依赖表、`08-sharing.md` 已知限制同步改为四档说法。

## 2.3.1

- `compile_study_pdf.py` 加 `--keep-aux`：编译失败时把 `.tex` / `.log` / `.aux` 复制到输出旁的 `<名字>.build\`；成功时仍只在临时目录编译、产出目录只有 PDF（06 补说明，07 命令表同步）。

## 2.3.0

- 新增 `scripts/qbank_import.py`：一条命令把 StudyHub 题组导进本地 `题库.jsonl`（只读插件数据、按「题组标题 / 卡片 id」去重、不动作答与排期）。
- `09-local-store.md` 第五节改写：从「手工四步」改成「一条命令 + 兜底说明」。
- `SKILL.md` / `README.md` / `07-environment.md` 补该脚本的说明与命令。

## 2.2.0

参照 good-learning 与 StudyHub 源码的做法重写（不照搬，按本技能的判据改写）：

- **排期换成 FSRS 式两参数**（`stability` / `difficulty`）：答错不再一律归 1 天，按遗忘曲线压；新增 `qbank.py exam` 把到期日限制在考试日之前（`unaligned_due` 留原始日期）。
- **四种作答不算数**（`retry` / `self-reported` / `implicit` / `simulated`）：只留痕迹，不进掌握、不动排期、不进错题本；`stats` 单列「不计入掌握 N 次」。
- **顽固题**：累计失败 ≥3 次或近 5 次错 ≥60% 触发，处理顺序「换更少步骤的同源题 → 做得成是绕不是不懂 → 做不成退前置 → 近 5 次全对自动解除」，并直接进下一次回测。
- **收题六问**：自足 / 不泄答案 / 选项像样 / 考要点 / 有出处 / 解释说得通，任一不过就换题。
- **产出目录规范**：顶层只放成品、源文件进 `源文件\`、不预建空目录、不把没做完写成做完。
- **标题即排版指令 + 双版式**：`## 单元 N` / `## 独立练习` / `## 答案` 自动分页；讲解版不留白、练习版按题型留白（选择 25 / 计算 35 / 证明 45 mm）。
- **知识卡**：每卡必带一条易错点或一条自检；节点超 6 个分两页，每侧最多 3 张卡。
- **材料分层**：考纲真题 → 教材 → 课件 → 习题笔记，结论只能有一个出处，都查不到就标「未覆盖」。

## 2.1.0

题库与排期改成**双后端**，不再强制依赖 StudyHub：新增 `scripts/qbank.py`（`题库.jsonl` / `作答.jsonl` / `排期.json`，排期用 FSRS 式两参数）与 `references/09-local-store.md`；`config.json` 加 `store: studyhub|local`，`init.py` 加 `--store` 与第四个问题；`SKILL.md` 第一条铁律从「只放 StudyHub」改成「只放一处，两条路不混用」，十步法与分流表补本地落点；`02-lesson.md` / `03-review.md` / `07-environment.md` 相应处补「有插件 / 本地」对照；README 与 `08-sharing.md` 的依赖矩阵改成二选一，已知限制第 5 条改成「FSRS vs 简化 SM-2 的精度差」。

## 2.0.1

分享前审计修了八处：`config.json` 不再随包（加 `.gitignore`，README 与 08 写明只发 `config.example.json`）；`SKILL.md` 里 `build_kb.py` 的子命令与 `rebuild` 描述改成真实存在的命令；`map-config.example.json` 改成 `knowledge` / `plan` / `day` 三键、节点用 `title` + `lines`，`render_study_pdf.py` 加字段兜底（`label` → `title`、`lines` 缺省）且示例每键 6 节点；`export_studyhub_md.py` 兼容 `page` / `text` 的旧库并加 `--db`；`compile_study_pdf.py` 支持传目录批量编译、找不到编译器时读 `config.json` 的 `texlive_bin`；`init.py` 遇到已有配置返回 1 并说明；`check_env.py` 不再自动建目录（只报 WARN）；Windows 控制台统一 UTF-8 输出；README 与 07 补 demo 材料与 `pip install` 说明。

## 2.0.0

- 拆成复合技能：`SKILL.md`（主入口，约 130 行）+ `references/` 八篇 + `scripts/` 七个 + `assets/` + `README.md`。
- 新增通用建库流程（`references/04-kb.md` + `scripts/build_kb.py`）：只讲怎么建，不绑定任何既有库；支持 SQLite + FTS5，也说明 Markdown 目录与向量库两种替代形态。
- 新增材料解析自选矩阵（`references/05-materials.md`）：照片 / PPT / 扫描件 / 矢量 PDF 四条线，每步写「没有某工具时用哪个顶」。
- 新增 `scripts/init.py`（生成 `config.json`）与 `scripts/check_env.py`（六项自检 + 缺什么影响哪一步）。
- 新增 `references/08-sharing.md`：依赖矩阵、安装三步、隐私边界、已知限制。
- 去掉本机绑定：绝对路径改成 `config.json` 的键、五门课的硬编码课名与知识库 CLI 变成可选后端、会话识别码改成配置项。
- 新增 `assets/`：进度表与能力表模板、依赖图配置示例、三讲 demo 材料。

## 1.x

- 单文件版（约 400 行）：开课五问、每讲七步、回测与周复盘、产出五件套、命令速查、禁区。
- 内置 PDF 脚本四个：试卷 + 答案册、清单 / 计划 / 依赖图、批量 .tex 编译、StudyHub 导出。
