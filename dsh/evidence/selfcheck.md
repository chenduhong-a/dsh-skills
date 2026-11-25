# DSH 自检：案例与实测证据

> 本文件是案例与实测证据，执行时不必读。自检怎么查、判据是什么、报告怎么写，全在 `references/selfcheck.md`；这里只存它搬出来的具体读数、样本清单、事故经过与版本沿革。references 里的「依据见 `evidence/selfcheck.md` 第 X 节」指向本文件；节号沿用原 `selfcheck.md` 的编号，搬运处尽量保留原句。
>
> 覆盖范围：原第 0 / 1 / 2 / 4 节与第 5.1 / 5.3 / 5.4 / 5.5 节、第 6 节中属「具体读数、样本、事故、沿革」的部分；第 3 节报告格式是硬规定，整节原样留在 references，未搬。第 5.2 节的四类修法亦全部留在 references。

## 0. 脚本与落档（原第 0 节）

- 原文标着「**脚本性质与时区（2026-11-06 记 / 2026-11-13 复核）**」：零依赖，只用 Node 内置模块 + `node:sqlite` 只读直读记忆库；同目录另有 `README.md`。多工作区由 `WS` 常量驱动（cwd 含 `.dsh-mind` 就用 cwd，否则退回 `C:\deepseek\work`）：记忆库、落档目录、可清清单、残留扫描、差分标签全部随 WS。
- 运行耗时口径：`--full` 约 20 秒、`--quick` 约 10 秒、`--only` 秒级（原第 0 节的经验值，非硬指标；脚本头注的 20~40 秒是会话多时的上限）。
- 落档文件名用本地时间，格式 `<本地时间>-<模式>.json`。
- **单副本约定（2026-11-24）**：`scripts\selfcheck.mjs` 此后只有技能里这一份，不再维护 `C:\deepseek\tools\` 的旧副本、也不做哈希校验；旧的双副本维护要求只作历史。

## 1. 十二项（原第 1 节）

- 03 三方插件：表格规则的时间线——「2026-11-10 定「一个插件一行」，2026-11-17 追加「别分组」」。
- 07 记忆：原文括注「**库路径按 cwd 优先**……（2026-11-13 改，脚本输出会标「库=」）」——该轮把库路径从固定路径改为按 cwd 优先。
- 07 记忆：原文括注「脚本末尾会打印**待人工对账**四件（2026-11-19 加）」。
- 08 工作区：原文括注「**根目录按 cwd 优先**（2026-11-13 改）」。
- 取数细则：出处「2026-11-13 / 2026-11-03」；工作区可见阈值的由来——「原 work 专用白名单会让 study 的大块子目录整个不可见」，故改为全量子目录里 ≥20 MB 或 ≥200 文件。

## 2. 四个哨兵（原第 2 节）

- 注入判据的来由：2026-11-11 明确——本轮没有注入块但 `memory_search` 正常，判为「关键词未命中」，不算故障；要强验证就开个新会话看首轮有没有横条。
- `univer_` 建文件接口的禁令经过：2026-11-07 用户明确否掉——「会在侧栏弹出文档窗、服务把文件锁死删不掉，`%TEMP%` 还会被 `SESSION_SCOPE_DENIED` 拒绝」。

## 3. 报告格式（原第 3 节）

- 本节无搬运：六条硬规定与总判据一字未动留在 references。

## 4. 异常速查（原第 4 节）

- 「`failed to prepare profile bundle` / 插件工具全消失」那条修法是 2026-11-14 用户要求补进自检的（原文括注）。

## 5.1 插件说明对账（原第 5.1 节）

- **2026-11-19 同步后的基准**：内核 0.2.2-rc.5 / 26 deps 38 bundles，265 行 / 约 38.7 KB，条目记到第 24 条；现行补丁 **6 组**（第 6 组＝billion 压缩闸放行，脚本 `dsh/scripts/billion-ungate-patch.cjs`）。
- 为什么必须当轮改（原文）：「插件说明是「下一次谁来看都能信」的权威文档，版本号一落后就会误导人——2026-11-09 发现它停在 10-20，还写着 13 依赖 / 22 bundle、billion compat、内核 0.2.1-rc.2，全部是错的。**自检时不顺手改，它就永远是错的。**」

## 5.2 记忆库体检（原第 5.2 节）

- 本节无搬运：四类问题与修法、判据、层级写法全部留在 references。

## 5.3 SKILL.md 与 `selfcheck.mjs`（原第 5.3 节）

- 2026-11-20 复核时脚本 **569 行 / 29,192 B**（当时还维护双份，现已废）。
- 该版改动：在 `--quick`/`--full` 末尾加「待人工对账」四件清单与超长计数、头注释「九项」改「十一项」、`PURPOSE` 表旧包名 `dsh-pdf-enhanced` 改 `dsh-doc-parser`、删掉 3 个已卸包并补齐 6 个缺条目、修好 `--only 03` 不出插件清单的绑定 bug。

## 5.4 更新检查（原第 5.4 节）

- 红点第①类样本（2026-11-13）：`file:`/`link:` 本地装、npm 查不到 → 必然红：daily-flashcard / knowledge-base / structured-prompt / power-menu / pptx-formula / research-toolkit / step-pause 七个。
- 红点第②类样本：bili-vision `git+https://gh-proxy.com/...`，检查器访问 GitHub 直连失败报 `ECONNRESET`。
- 红点第③类样本（点了会降级）：structured-prompt `0.5.0→0.4.1`、daily-flashcard `4.6.2→4.5.1`。
- npm latest ≠ 上游最新版的具体读数：StudyHub（`@ericwang1358/dsh-daily-flashcard`）只在 GitHub release 发版，npm latest 长期停在 4.5.1、GitHub releases 已到 **v4.13.0**（2026-11-18T07:58Z），面板红点一直亮着而实际落后两个版本。
- 技能引用失效的样本：2026-11-13 doc-parser 改名就扫出 37 处旧工具名。
- 版本号噪音样本：billion-context 的作者 CI 每几分钟给每个 PR 发一个预览版（`0.0.8580-pr.5905.5456a28` 这种、几百个 tag），`master` 是主干快照（`0.0.1081-master.6df7ae1`），版本号都是 0.0.x 且随时变。

## 5.5 GitHub 源检查（原第 5.5 节）

- 包清单沿革（原文）：「**范围**：`package.json` 里有 `repository` 字段的非 registry 包（2026-11-14 是 7 个：StudyHub / structured-prompt / power-menu / research-toolkit / step-pause / bili-vision / raw-html-v2）。（2026-11-16 复核：非 registry 包共 8 个＝上列 7 个 + `link:` 装的自研 `dsh-doc-parser`，无 repository、无上游，不进本步。）」
- `releases.atom` 实测：本机一句 `Invoke-WebRequest -Proxy` 就能取到整篇 release 正文，不占 API 配额、403 限流时照样能用。
- 已知上游表的历史行：「`@local/dsh-knowledge-base`（**2026-11-16 已卸载**）→ `KingsleyAsher/Personal-Knowledge-Base`——作者未在 package.json 写 repository；npm latest 长期不动，只发 GitHub release（v3.1.1 于 2026-11-14）。**插件已于 2026-11-16 从 profile 卸载**，条目留作重装时查上游。」
- 上游地址表 2026-11-14 起手工维护。

## 6. 不许做的事（原第 6 节）

- 「不许凭印象说体积」的反面案例：曾把 3809 MB 的 node_modules 里最大项说错。
- 「不可动清单」的历史变动：「`work\_pdftest` 2026-11-09 删除、`dsh-doc-parser\ocr-venv` 2026-11-18 随 Indra 移除，均不再在列。」
- 插件清单规则：2026-11-10 定「一个插件一行」，2026-11-17 追加「别分组」。
- 更新检查「只报告、不自动升级」：2026-11-14 定。

## 7. 版本沿革（按日期）

- 2026-11-03 取数细则成形。
- 2026-11-06 脚本性质与时区首次记录。
- 2026-11-07 禁用 Univer 建文件接口造探针（用户否掉）。
- 2026-11-09 要求三方技能附简介；发现插件说明停在 10-20；`work\_pdftest` 删除。
- 2026-11-10 插件清单定为「一个插件一行」。
- 2026-11-11 记忆注入判据：无注入块但 `memory_search` 正常＝关键词未命中，不算故障。
- 2026-11-13 库路径、工作区根改为 cwd 优先；工作区阈值改 ≥20 MB 或 ≥200 文件；doc-parser 改名扫出 37 处旧工具名；红点三类样本。
- 2026-11-14 加入更新检查与 GitHub 源检查；Clash 预热 6 秒、用完等 4–5 秒；profile bundle 空壳修法补入；定「只报不升」。
- 2026-11-16 `@local/dsh-knowledge-base` 卸载；非 registry 包复核为 8 个。
- 2026-11-17 插件表「别分组」。
- 2026-11-18 StudyHub GitHub releases v4.13.0（07:58Z）；`dsh-doc-parser\ocr-venv` 随 Indra 移除。
- 2026-11-19 脚本加「待人工对账」四件与超长计数；要求汇报附更新说明；插件说明基准同步到 0.2.2-rc.5 / 26 deps 38 bundles。
- 2026-11-20 脚本复核为 569 行 / 29,192 B（读数见 5.3 节）；`dsh-qqbot-bridge` 已卸。
- **2026-11-20 17:32 换装 meow-mind 后**：脚本 29,774 B（当时双份一致，`C:\deepseek\tools\selfcheck\selfcheck.mjs`）；改动三处：①记忆库判定改为 `.dsh-mind` 优先、旧 `.dsh-meow` 兜底；②活跃口径从 `status='active'` 改成 `status IN ('active','memory','evolution')`（新库没有 `active`，不改恒为 0）；③`PURPOSE` 表 `meow-memory` 换成 `meow-mind`。实测 `--only 07` 读到新库 437/933、db 8.36 MB。
- **2026-11-20 18:02 自检后**：脚本 **29,805 B / 575 行**（当时双份一致）；`PURPOSE` 表 meow-mind 条目从「13 工具 + 关系网 + 自动捕获」改成「**14** 工具 + 关系网 + 自动捕获 + `/dream` 指令 + 沉淀候选」。**修的口径漂移**：插件后来加了第 14 个工具（`memory_feedback`），表里仍写 13，自检输出就跟着报旧数——加工具时 `PURPOSE` 表的数字要同步。
- **2026-11-21 13:08 自检**：26 deps / 38 bundles（与基线一致，掉队 0 / 多余 0）、26 个插件、记忆 444 活跃 / 946 全量 / db 8.59 MB、工作区 216.4 MB / 295 文件（差分 683→216.4，因为 11-20 删了 meow-mind 的 464 MB 开发依赖）、HOME 6921.6 MB。**新澄清的一个口径**：脚本报「>800 字 0 条」是**活跃口径**（`status IN ('active','memory','evolution')`）；**全库不限状态**其实有 **51 条 >800 字，全部是 `review` 状态**——它们是迁移时从旧库 `archived`/`stale` 映射过来的沉淀，不参与注入、不参与排序，**不是漏报也不是待修问题**。报超长时必须说明是哪个口径，否则读数看着自相矛盾。
- **2026-11-21 13:12 脚本改动**：`selfcheck.mjs:195` 的 `source` 判定补上 `git` 分支——原来只有 `link:` / `file:` / 其余一律 `registry`，而 `bili-vision` 的 spec 是 `git+https://gh-proxy.com/https://github.com/icyaaaww/dsh-bili-vision.git#v0.2.0`，被误判成 registry 后更新检查会去查 npm（必然 404）。新判定 `spec.startsWith('link:') ? 'link' : spec.startsWith('file:') ? 'file' : /^(git\+|github:|gitlab:|bitbucket:|https?:\/\/\S+\.git)/.test(spec) ? 'git' : 'registry'`。脚本 **30,026 B**（当时双份一致，`node --check` 通过），`--only 03` 复跑确认 `bili-vision` 现在显示 `git`。**教训**：`selfcheck.mjs` 的 `--only` 编号只到 10，**更新检查不在脚本里**，是我按本文件手动做的第 11 项——别去 `--only 11`。（2026-11-26 更正：脚本已加 `--only 11` 别名，内部映射到 03。）
- **2026-11-21 更新检查结果**：registry 装 17 个（不是 18，`bili-vision` 是 git）——**`cc-safety-net 2.8.0 → 2.8.1` 可更新，其余 16 个已最新**。2.8.1（2026-11-20）的内容：rulebook v2 可声明 `options_with_values`（带值选项先出现时 `command_path` 仍能匹配，如 `kubectl -n payments delete pod api`）、fixture 校验改成走 hook 实际用的分析器（`sudo`/`env FOO=1`/`timeout 30`/`bash -c` 这类包装写法现在能作为有效 `blocked` fixture）、**安全修复：fixture 评估不再碰文件系统**（防下载的 rulebook 让 CLI 读任意路径）。**对本机的实际影响很小**——我们用默认规则集、没写自定义 rulebook，`options_with_values` 用不上；但 fixture 分析与安全修复属底层逻辑，升级无兼容风险。
- **`cc-safety-net` 的管理入口是 `dist\bin\cc-safety-net.js`**（2026-11-21 实测）：跑 `dist\cli.js` 静默无输出、也不报错，容易被当成「命令没执行」；改规则/查状态走 bin 入口，有 `--help` 输出才算跑对。
- **2026-11-21 记忆体检处置**：①`project 0mvuk4zug-…`（569 字）整条还在描述已卸载的 meow-memory 0.33.1（工具 7 个、库 `.dsh-meow`、`promptLang` 配置）→ 改写成 meow-mind 0.1.0 现状（14 工具、双通道召回、关系网、`/dream`、自动捕获、三条纪律），标题回填、importance 2→3；②`topic 0mw4te8v4-…`（474 字）里「库在 `.dsh-meow`、dream_log/windows/dream_meta 三表、393 active / 886 全量」→ 改成 `.dsh-mind`、新表清单、444/946，并补一句「review / archived 状态的长条目不算超长问题」；③`project` 列 `meow-memory` → `meow-mind` **12 条**（4 条活跃 + 8 条 review），`memory_update` 没有 `project` 参数，只能 SQL 直改。**技能引用复核**：24 处命中旧名，全部合规——`evidence/*.md` 里的历史案例（带日期、是证据）、`selfcheck.mjs:44/46/50/53/76` 的 `.dsh-meow` 兜底判定、`memory-collab` 与 `selfcheck.md` 里「旧库只作回滚保留」的说明性文字。**没有一处要改**。
- **2026-11-21 13:15 B站 cookie 的 mtime ≠ 有效性（措辞纠正）**：13:08 那份报告写了「cookie 32 天，可能开始掉登录态」，**这是错的**。`bili cookie` 报的是 `C:\deepseek\tools\bili-mcp\cookie.json` 的**文件 mtime**，不是会话过期时间。实测起 server 后 stderr 明说 `✅ Cookie 有效，用户: 尘渡红`，`bilibili_video_info` 真调也成功。**判据改成：不看文件天数，看 server 启动日志那行「Cookie 有效，用户: X」或真调一次登录态接口**。另外 `bilibili_refresh_cookie` 需要 `BILIBILI_REFRESH_TOKEN` 环境变量（浏览器 `localStorage.getItem('ac_time_value')` 或扫码登录），缺它就报 `isError: true`，**这不代表 cookie 坏了**。
- **2026-11-21 13:16 B站工具数是 31 不是 22**：server stderr 打印 `📋 Tools registered: 22 个工具`，但 `tools/list` 实际返回 **31 个**，与自检 JSON 的 `bili.mcp.names` 集合完全一致（差集两边都是空）。**以 `tools/list` 为准**，stderr 那个 22 是它自己的日志口径（可能只统计了启动时静态注册的那批）。

- **2026-11-24 10:15 自检**：内核 `0.2.2-rc.5`（cli=exe）、electron 44.7.0、26 deps / 38 bundles（掉出 0 / 多余 0）、**25 个插件**（比 11-21 的 26 少 1 个，未逐个比对是哪只）。记忆：**2 活跃 / 538 全量**（soul 1 · user 22 · project 152 · fact 1+175 · lesson 1+120 · topic 43 · rules 23 全 review）；536 条 review 的 `updated_at` 绝大多数是同一个毫秒 `1795241736821` = `2026-11-21T06:15:36.821Z`（**北京时间 14:15:36**，即 11-21 13:16 那条记录之后不久的一次批量归档），`lesson` 层就有 114 条落在该毫秒。用户裁定这批是「审议栏标记无用」，**保持不检索、不改检索口径、不动数据**；但 `memory_marks` 表里只有 **14 条 useless**，与该数量级对不上——批量来源未定论，将来有需要再核（不影响当前行为）。**两处修复**：①`PURPOSE` 表 meow-mind 从「14 工具」改成「**22 工具 / schema 5**」（`selfcheck.mjs:163`）；②`studyhub-preset-patch.mjs` 的 `js-yaml` 从 `createRequire(PROFILE/package.json)` 改为 `createRequire(import.meta.url)`，把 js-yaml 4.1.0 放到脚本同目录 `scripts\node_modules\js-yaml`（全机原本没有 js-yaml，profile 也没有），重放补丁 **3 处**（`study.patch.yml` 14900 B，22 plugins / delegation 5 行解析通过，`--check` 幂等）。其余：B站 31 工具真调 OK（cookie 判据见 11-21 13:15 条，不看天数）、旧包名引用 19 处全合规、MinerU 本地未起 / bsk=false / QQ 插件 false / GUI 端口 13049。落档 `C:\deepseek\work\handover\selfcheck\2026-11-24-10-15-43-full.json`。
- **2026-11-24 10:38 更新检查搬进脚本**：用户要求版本列带「是否最新」判定（此前 `--only 03` 只查 registry，`file:`/`link:`/`git:` 一律标「本地」跳过，等于没查）。两次改造：①加 `NPM_REG` / `cmpVer` / `npmLatest`，`plugins()` 改 async 并发，三态「新 / 旧 → x.y.z / 本地」；**只比是否落后**——本地领先上游也算「新」，否则 daily-flashcard 本地 5.3.3 > npm 4.13.0 会被标「旧 → 4.13.0」诱发降级。②「本地」那批再按 `package.json` 的 `repository` 查 GitHub tag：`parseGithubRepo` + `ghTags`（`data.jsdelivr.com/v1/packages/gh/<o>/<r>` 的 `versions[].version`），四态「新 / 旧 → x / 自研 / 无 tag」。**jsdelivr 直连可用、不需要代理**（实测 4 个仓库 1 秒内返回）；GitHub API 当天不通——Clash 起了、7897 在听，但 `Invoke-RestMethod -Proxy` 报 `The SSL connection could not be established`、`curl.exe -x` 给 `http=000`（节点未就绪），按规矩 5 秒后关掉。复跑 `--only 03`（3.7 s）：**新 22 / 待升级 1 / 自研或查不到 3**，唯一落后 `dsh-power-menu 0.1.22 → 0.1.23`；`dsh-raw-html-v2` 上游 `plolpl789/dsh-raw-html-v2` 无 tag 查不到；`dsh-doc-parser` / `meow-mind` 自研无上游。同日 7 个 registry 包已升（deep-whale-manager 0.1.11 / maid-atelier 0.1.12 / orca-link 0.1.12 / cc-safety-net 2.8.3 / dsh-context 0.87.1 / dsh-prompt-rewriter 1.9.0 / dsh-univer-office 0.5.2），每次 `dsh plugin add` 都 exit 1 但版本已变——`ERR_PNPM_IGNORED_BUILDS`（onnxruntime-node@1.30.0 / protobufjs@7.6.6）的噪音，`.npmrc` 被 cc-safety-net 拦、`pnpm-workspace.yaml` 的两个开关都不生效，已回滚原样。
- **2026-11-24 10:42 dsh-power-menu 0.1.22 → 0.1.23**：用户续费代理后 `-Proxy http://127.0.0.1:7897` 恢复可用（api.github.com 0.7 s，此前 SSL/超时是订阅过期）。Release `v0.1.23` 资产 `dsh-power-menu-0.1.23.tgz`（109655 B）+ `SHA256SUMS.txt`，下载后 sha256 `ee67ef882589ec0b8c09a2e685f13c2e3b6c970e60cd43e5325684af0841ecdc` 与清单一致；`dsh plugin add "file:C:/deepseek/tools/archives/dsh-power-menu-0.1.23.tgz"` 报 `- 0.1.22 / + 0.1.23` 但 exit 1（仍是 `ERR_PNPM_IGNORED_BUILDS` onnxruntime-node / protobufjs 的噪音，见 ops 1.9）。三条验收：spec 变 0.1.23、node_modules 版本 0.1.23、bundles 仍 38 且含该包。复跑 `--only 03`：**新 23 / 待升级 0 / 自研或查不到 3**，全机已无待升级。SHA256SUMS 留在 `C:\deepseek\tools\archives\SHA256SUMS-0.1.23.txt` 作证据。

- **2026-11-24 12:40 第 12 项「使用统计」进脚本**（源自 nagi-studio/skills 的 `checkup` 审计脚本，只借口径不装它）。数据源四类，全从 `$DSH_HOME/sessions/**/session*.jsonl.zstd` 的 `tool/call` / `user/message` / `request/header` 解出来：①工具调用按前缀归插件（`TOOL_OWNER` 表，未命中记「内核 / 其它」）；②`skill` 工具的参数名＝模型自动触发；③`<skill_content name>`＝用户手动触发、`<available_skills>`＝技能目录常驻字符；④`data.header.tools` 的 JSON 长度＝工具 schema 常驻字符。**最大的坑是多帧 zstd**：DSH 的会话日志是每批写入一帧拼接的，Node 24.21.0 的 `zlib.zstdDecompressSync` 和流式 `createZstdDecompress()` **都只解第一帧**——88.4 MB 的文件只解出 198 字节，`--only 12` 直接抛 `ZSTD_error_prefix_unknown`。按 RFC 8878 手算帧长（magic 4 + FHD 1 + FCS 1 + block 156 = 165）也不对，Python `decompressobj()` 给出第一帧 169 字节、差 4 未查明；**最终不解析帧头，改用 `buf.indexOf(ZSTD_MAGIC)` 扫全部帧起点逐帧解**（`ZSTD_MAGIC = 28 b5 2f fd`）：最大文件 51780 帧 / 88744 行 / 245,115,576 字节输出 / bad=0 / 1.8 秒，整轮 185 会话 6.1 秒。与 Python 版（`_audit.py` 加 `zstandard` 0.25.0 后 9.6 秒）对比：tools_count 都是 116，tools_schema_chars 142162 vs **136828**——差异是 Python `json.dumps` 带空格、Node `JSON.stringify` 不带，以 Node 为准。**首轮真实底数**：常驻工具 116 个 / 136,828 字符 + 技能目录 13,121 字符（合计 ≈ 150 K）；30 天 31865 事件里 22 个技能被触发，零触发 `doc-parsing`、`kb-ops`；插件调用 `内核/其它 23833 · meow-mind 5343 · browser-skill 688 · modsearch 321 · dsh-doc-parser 262 · daily-flashcard 132 · a2ui 78 · visual-card 46 · bili-vision 25 · univer-office 7 · research-toolkit 2 · structured-prompt 1`；工具 top `pwsh 10558 / read 3536 / memory_update 2665 / edit 2304 / write 2181`。**编号撞车的处理**：文档第 11 项原本是「更新检查」，而更新检查早已由 `--only 03` 的四态判定承担，所以脚本里 `11` 让位给「使用统计」→ 改成 **`12` 使用统计**，`--only 11` 自动映射到 `03`（旧命令继续能用）。`--full` 22.7 s，落档 `C:\deepseek\work\handover\selfcheck\2026-11-24-12-38-55-full.json`。

**2026-11-24 13:00 卸载 dsh-video-understand 0.5.2（26 deps / 38 bundles → 25 / 37）**——用户理由「与 bili-vision 重复」。dsh plugin --profile desktop remove 2.5 秒、exit 0、无 IGNORED_BUILDS 噪音；
node_modules 该包 7,392 文件 / 2,441.2 MB 全删，profile 的 node_modules 从约 3.86 GB 降到 1,421.4 MB / 29,594 文件；~\.dsh 与 C:\deepseek\插件 无残留。**纠正一条旧记录**：onnxruntime-node（236 文件 / 287.7 MB）不是视频插件的传递依赖，dsh plugin why onnxruntime-node 显示 meow-mind → @huggingface/transformers@4.3.2 → onnxruntime-node@1.30.0——历次 exit 1 里的 ERR_PNPM_IGNORED_BUILDS: onnxruntime-node@1.30.0, protobufjs@7.6.6 也是它，与 video 插件无关。**连带修复（ASR 通道）**：bili-transcript\scripts\transcript.mjs 原写死 
node_modules\dsh-video-understand\.venv，随包消失 → 改指 ~\.dsh\bili-vision-venv（faster-whisper 1.2.1 / ctranslate2 / av / numpy / yt-dlp 2026.11.23，510 MB）；asr.py 从 插件\patches\video-understand-0.5.2\ 复制进技能 scripts\。踩两个坑：①直接传 wav 路径给 faster-whisper 1.2.1 报 open() got an unexpected keyword argument 'metadata_errors'（av 19）→ 改成先解码成 numpy float32 再喂模型；②ctranslate2 报告 cuda 可用但 venv 里没有 cublas/cudnn（那套 2 GB nvidia 包原在 video-understand venv）→ 加 CPU 自动回退。实测 FORCE_ASR=1 跑 BV1VbytzAE2D：573 秒视频 70.3 秒、305 段、格式 [mm:ss] 正确。文档同步：bili-transcript\SKILL.md（description + 注意节两条 + 路由那条）、DEPENDENCIES.md（venv 行与 yt-dlp 行、脚本节加 asr.py）、~\.dsh\AGENTS.md（第 3 条与技能表）、本技能 scripts\README.md（不可动清单删 nvidia 项）、references\ops.md 1.9 条（onnxruntime 归属纠正）、selfcheck.mjs（DO_NOT_TOUCH 删 nvidia 项、PURPOSE 表删 video-understand、TOOL_OWNER 删 video_understand 映射）。

**2026-11-24 13:50 第 12 项两处修正（AGENTS.md 计量 + 工具面取最全）**——①常驻开销原来只算「工具 schema + 技能目录」，漏了 user-global `AGENTS.md`（每请求都注入、都付费），补 `usage.agentsMdChars`（读 `\/AGENTS.md` 字符数）与「常驻合计 ≈ Nk token」一行，超 180 K 字符时打 ⚠ 提示「把长内容挪进技能或样板」；②`header` 原来每次都覆盖，留下的是**最后一个** `request/header`，数字随扫描顺序漂移——同一台机器上一轮跑出 116 个 / 136,828 字符、下一轮 110 个 / 96,609 字符。改成同时记「最全」（header）与「最省」（minHeader），输出带区间。**修正后的真实底数**：工具 **143 个 / 158,301 字符**（会话间 19 个 / 14,263 字符 ~ 143 个 / 158,301 字符），技能目录 13,006 字符，`AGENTS.md` 5,963 字符 → **常驻合计 ≈ 55.4k token**（按 3.2 字符/token 估）。此前所有「116 个 / 136.8 K ≈ 34k token」的说法只是某一次会话的快照，偏低约 60%。落档 `2026-11-24-13-50-19-full.json`（18,924 B，25 deps / 37 bundles）。文档同步：`references/selfcheck.md:45` 第 12 项那格补了 AGENTS.md 与「工具面按会话漂移、别取最后一个 header」；同次还把 `AGENTS.md` 零节加了「先查外部现成实现 + star 不作判据 + 没许可证的仓库能看不能拿」，并新增「开工前先拷打需求（3 档）」小节（128 行 / 5270 字符 → 148 行 / 5963 字符）。

**2026-11-24 13:56 第 12 项补五项口径（吸收 checkup 的 `audit.py` 口径，不装它的脚本）**——①MCP 工具单列 `mcpTools`/`mcpChars`：按 `mcp__` 前缀取到 0，本机 B 站 MCP 的工具名是 `bilibili_*` 平铺，脚本注明「需人工核对」；②零触发技能按 description 字符降序（输出 `doc-parsing(374c), kb-ops(267c)`）；③同名技能 `dupNames` 检测（后加载静默覆盖前面的）；④`disable-model-invocation: true` 记 0 字符；⑤**硬闸门 `schema_unrecognized`**：`sessions >= 5 && events === 0` 时输出「扫到 N 个会话但识别 0 事件：日志格式可能已变，本次用量结论不可用」并停——解析失败不能安静地表现成「没人用」。同批还改了 06 段：`fmValue()` + `skillMeta()` 读 frontmatter，`extraKeys` 只报 SAFE_FM（name/description/author/version/license/whenToUse/tags/metadata）之外的字段（改前把 `author` 也报成多余字段），返回 `{ user, pluginCount, byPkg, dupNames, catalogChars }`；`idleSkills` 按字符降序。**实测**：`--only 06` → 13 个自建 + 插件自带 24 个，目录估算 10,547 字符（自建 4,012）；`--only 12` 6.8 秒 → 143 个工具 / 158,301 字符（区间 19–143）、技能目录 13,006、AGENTS.md 5,963、常驻合计 55.4k token、MCP 0；`--full` 21.7 秒全通、冒烟 true、落档 `2026-11-24-13-56-07-full.json`（差分基线 `2026-11-24-13-56-01-full.json`）。同批把 `dsh\SKILL.md` 第 4 节验收段重写成四级拦截（结构消除 > 一犯就报错 > 一眼看见 > 写进 AGENTS.md），`~\.dsh\AGENTS.md` 十二节加「同一规矩只放一处」「报网络不通前先分三步」。

**2026-11-24 13:57 插件自带 skill 审读（24 份）**——C 组调研（第 7 集 `checkup`）点出的安全面，派 `skill-audit-1`/`skill-audit-2` 两个子代理读正文（我们此前一份都没读过）。产出 `C:\deepseek\work\调研\skill审读-univer与modsearch.md`（13 份）与 `skill审读-study与工具类.md`（11 份 / 158 行）。结论分布：**干净 12 / 质量疑点 11 / 需人工读 1**。唯一实质风险面是 `modsearch`：`SKILL.md:5` `allowed-tools: Bash` + `:45` 让人 `npx --yes --package @liustack/modsearch@5.10.14` 现场下载执行（13 份里唯一这组合），且 `:76` 写明 Firecrawl / Keenable **默认走云端浏览器**（内网页面会被甩上云）——但 `run.ps1:259-261` 只转发参数、`:17-18` 自述无 postinstall，`dist/main.js` 搜 `.ssh/.aws/.gnupg/.netrc/Cookies/SESSDATA/id_rsa` 全 0 命中，**当前无恶意证据**。三处「免再确认写入」：`study-book\SKILL.md:13` `Do not ask again before saving`（聊天里任意一句改书请求即视为授权，同文件 `:14` 还允许改学习者自己的 mine/qa 笔记）、`study-tutor\SKILL.md:44` 两次答错后不问就 `companion.compile(..., "attach": true)` 挂库、`study-coach-team\SKILL.md:83` 学习者一句「直接执行」可跳过写入前确认。常驻成本：24 份 description 合计 6,107 字符，`office`/`office-docx`/`office-pptx`/`office-xlsx` 四个别名路由合计 551 字符且零独有内容（纯路由税），univer 系 8 份以 `Use proactively ... any <Unit> task` 收尾属域内强触发。B 层补：`scripts\study-cli.mjs` 229 行无网络出口、不读敏感路径；`prepare.mjs:18` 的 `spawnSync` 是构建脚本无技能引用；`bsk_*` 与 `research_*` 能力核对为真，`mcp__matlab__*`/`zotero_*` 实调 `not_registered` 但正文自带「未连接须如实报告」，属有条件宣称。