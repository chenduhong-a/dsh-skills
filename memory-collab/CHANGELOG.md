# CHANGELOG

按 `skill-authoring` 的口径记「哪次改了什么、为什么」，不记流水账。

## 2026-11-26 — 按调研报告整修（实测瘦身 + 口径统一）

- **`references/memory.md` 缩到 199 行**（原三百三十余行）：判据留在正文（§1–§13，加段号），带日期的实测与来龙去脉整批迁进新建的 `evidence/measurements.md`；正文每条实测改成「一句结论 + 指针」。
- **字数上限从四套并成一张表**：`fact` 60、`rules`/`lesson` 250、`topic` 300、其余 200 字；压缩触发器统一写成「硬上限的 80%」。原先 450 的触发器高于 250 的硬上限，导致 `rules`/`lesson` 永不触发；`topic 300` 与「目标 480」两处重复口径一并删掉。
- **层数与表数对实**：九层补 `principle`/`todo`（原七层漏两行）；时间线是**五表**不是四表；`status` 六态表删掉「取值以下一行为准」的自指句。
- **作用域合成一条**：默认只写当前工作区库，全局库仅跨工作区时写；`memory_home` 按 0.1.2 源码改成「只读、无参、不迁移」（原「带 target 迁移」是旧说法）。
- **命令补全**：索引重建给可直接执行的三条命令（`$NODE_BIN` / `Join-Path` 符号），删掉未定义的 `...` 与字面绝对路径；准则文件节数改成现场数（`Select-String -Pattern '^## '`）。
- **与 `skill-authoring` 的冲突以它为准**：删「60–120 字」「绝对路径」两处旧口径；固化门槛改成**第三次**（原先把门槛写成「重复第二次就固化」）。
- **`SKILL.md`**：选篇表从一个单元格塞 13 个主题改成一主题一行（15 行，含 `evidence/`）；停止条件 4 → 6 条（`memory_*` 整片 unknown 先查 bundles；cwd 不是目标工作区先 `memory_home`）；验收加可执行断言。
- **`references/collab.md`**：只做 4 处小改（头部加符号与 evidence 指针、任务书第 3 条 node 绝对路径改 `$NODE_BIN`、`_relay` 三处标为历史机制）。结构与正文不动——这一篇是全技能最成熟的部分。
- **`DEPENDENCIES.md`**：meow-mind 0.1.0 → **0.1.2**；判据拆成三样（库 → `memory_health`；启用 → bundles + profile `package.json`；信箱 → `memory_mail stats`）；脚本跑法只留 `$NODE_BIN` 一种，删掉 `ELECTRON_RUN_AS_NODE` 老路。
