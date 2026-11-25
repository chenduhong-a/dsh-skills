# 实测记录（memory-collab）

> 放带日期的实测数字、报错原文与来龙去脉；判据在 `references/memory.md` 与 `references/collab.md`，本文件不重复判据、也不当操作手册。
> **数据截止 2026-11-26**。旧数字会过时，引用前按记录的复现方法重跑一遍。

## 库与表（2026-11-26 读 meow-mind 0.1.2 源码核对）

- 插件版本 0.1.2，源码 `$TOOLS_DIR\meow-mind`，profile 里以 `file:` 装。旧文档写 0.1.0 是过期值。
- `src\db.mjs:250`：`const DEFAULT_GLOBAL_DIR = 'C:/deepseek/.dsh-mind-global';`——全局目录默认值写死在插件里，不是 `~\.dsh-mind-global`。
- `src\config.mjs:14-18` 三个配置项：`projectDir`（默认 `.dsh-mind`）、`homeDir`（全局目录覆盖，空＝平台默认）、`globalDir`（默认同上；空串＝关闭全局库，信箱一并停用）。
- `src\tools.mjs:438-449`：`memory_home` **无参数、只读**，返回两库路径与各层条数；旧文档「带 `target` 迁移 / 热切换」是更早版本的行为，0.1.2 没有。
- 时间线建表在 `src\db.mjs`，共 **5 张**：episodes:127、phases:146、decisions:166、personas:187、persona_traits:197。旧文档写「四表」是错的。
- 九层表：soul / user / project / fact / lesson / principle / topic / rules / todo；库里**没有 `memories` 表**。
- 列数：九层都带 `project`；`lesson` 13 列（多一个 `corrected`），其余 12 列。
- `scripts\rebuild-index.mjs` 的 `LEVELS` 数组只列 8 层（缺 `principle`）。跑重建时该层不参与，复核别拿 9 层当期望值；脚本不报错、静默跳过（2026-11-26 读源码发现，未改脚本——本次只允许改技能目录）。

## 字数与体量

- 2026-11-18 体检：405→370 active，147.1K→127.1K 字，归档 35 条。
- 批量精修一轮里子代理自报字数普遍偏小：自报 198，实际 206–293（主线必须自己复核）。
- 2026-11-26 修 `references/memory.md` 时发现四套字数上限并存：`250/200`、`topic 300`、目标 `480`、压缩触发 `450`。450 高于 250，导致 `rules`/`lesson` 永不触发压缩。已统一成单表并把触发器降到硬上限的 80%。

## 索引

- 2026-11-22：只 upsert 不 `delete` 的后果——全局库多 3 条孤儿向量，工作区多 658 条。
- 验收口径：末行 `PASS`（active = fts = vectors、异模型 = 0）。

## 时间线

- 2026-11-26 两库时间线 0 条。原因：旧标准要求「跨数周」才建事件，实际没有一个任务够格。2026-11-24 用户重定为「跨多轮、有明确目标」即可。

## 工具行为（踩过的坑）

- `memory_update` 只写正文，**不重算向量**（0.1.2）。
- `memory_marks` 只增不减：用户连着批改两次时旧标记仍在，处置前必须与当前 `status` 对一遍。
- id 前缀会撞：`0mvce0ck` vs `0mvce0cky`。报「未找到该 id」但条目明明在时，实际是第 7 位字母 `o` 被当成了数字 `0`。
- 时间戳写成 17 位微秒 → 被当未来时间 → 天数夹成 0、recency 恒 1，整库时效权重失效；必须毫秒。
- PowerShell `& $node -e "…"` 会吃掉嵌套引号（`\"` → "Expected unicode escape" / SQL `no such column "table"`）；node + sqlite 探针写成临时 `.mjs` 文件再跑。

## 准则文件与注入（2026-11-26 核对）

- `$DSH_HOME\AGENTS.md` 有 9 个 `^## ` 节（零–八）。旧文档写「十二节」是历史值。
- 注入由内核包 `@deepseek-ai/dsh-agent-instructions` 做：每条链 64 KB、`maxSourceBytes` 1 MB；先 `$DSH_HOME/AGENTS.md` 再 `~/.agents/AGENTS.md`。
- project 链靠 `projectRootMarkers`（默认 `.git`）定根；`C:\deepseek\work`、`C:\deepseek\study`、`C:\deepseek` 都没有 `.git`，project 链本机实际不生效，只用 user 级。

## 协作侧（`references/collab.md` 里的案例，明细记在这）

- 2026-11-09 派独立 agent 测插件：17 分钟交回 12 个 BUG，其中 1 个是主会话审了 1290 行没看出来的严重 bug（prefetch 结果被 IIFE 丢弃）。
- 并发实测：同一批 8 页、batch 2，3 路并发 25 秒 vs 串行 22 秒（服务端顺序排队，3 份 37 MB 文件互相争 CPU）——「允许 concurrency 3」不等于能并行加速。
- 审查类任务按域派两个只读代理：三轮共 35 条，比一个综合审查挖得深。
- 2026-11-18 用户原话：「避免上下文过长，污染，影响智力」（能拆就拆的由来）。
- 2026-11-19 用户定规「子代理优先建立可复用的」；同日发现已有 `doc-auditor`/`script-auditor` 闲置却又新建了 `doc-auditor2`/`script-auditor2`。
- 2026-11-21 用户原话「先按技能去重，把技能覆盖到的记忆删掉」；同日「发信的时候也要读信箱，别光写不读」。
- 2026-09-30 用户原话「你觉得怎么改好就怎么改，不用一直问我」——授权的只是「改」，永久删除与归档仍逐条先问。
- 2026-11-23 从 `qwen3.5-4b-memory-v2` 的抽取合同借来「原话与数字照抄，不要转述」。
- `_relay` 信箱时代的历史数据：from-other 16.7 KB→3.9 KB、from-lead 121→37 行；该目录 2026-11-26 核对已不存在，现役落点是 `memory_mail`。
