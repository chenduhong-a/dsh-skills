---
author: "ZQY-LB"
name: study-flow
description: "从头系统学任何一门课的完整流程（不绑定具体课程）。用户说「从头学一门课」「今天讲什么」「我学到哪了」「出一套测试卷」「总结这一章」，或在学习资料目录里要查教材原文与页码、把教材接进知识库、出题复习、做知识清单与 PDF、维护学习进度时；有明确考试日或目标分数（「考到 85」「过线」「拿省二」）要排备考计划时（见 `references/11-exam.md`），先读本文件：开课先问五件事，按答案分叉走完整条链；随堂题在会话里，课后题 / 试卷 / 章节总结 / 速查册 / 总总结按进度出文件。不用于只带教一个知识点并当场测（见 study-tutor）、写复习全书（见 study-book）、课件整理成册入库（见 study-intake）、一句话从目标建一门自学课（见 study-self）、在大书里按章节定制题型与范围（见 study-custom）、出征语音包与四助教课后会诊（见 study-coach-team）。"
---

# Study Flow · 从头学一门课

> 版本号见 `CHANGELOG.md` 顶部（当前 2.7.32）。frontmatter 里不写 `version`——技能加载器不读它。

复合技能的入口。**这里只放「走哪条、守什么」**；步骤在 `references/`，工具在 `scripts/`，模板在 `assets/`。

## 零、先看地图

直接上工具最容易做错层：拿 OCR 重跑已有教材、手写知识清单却该用库里数据、把「本人自出的题」当成本科书里真有。先判断这件事落哪一层。

| 层 | 是什么 | 什么时候用 |
|---|---|---|
| **底座 · 知识** | 一个能回答「这个词在哪一页」的库（默认 SQLite + FTS5，见 `04-kb.md`）；一门课一个 `course`，可按课过滤查条目 / 知识卡 / 例题 / 页码 | 查概念在哪一页、要原文、要原图 |
| **入口 · 材料** | 文档解析与导入（`05-materials.md` 的选路矩阵）+ 材料整理技能 `study-intake` | 新书、新课件、新照片进来 |
| **流程 · 学** | 本技能 `01`–`03`：排计划、逐讲带学、出题、回测 | 开课、讲、练、复盘 |
| **产出 · 纸与屏** | PDF：`06-output.md` → `scripts/render_quiz_pdf.py` / `render_study_pdf.py` → XeLaTeX；会话里的讲解卡片：`10-cards.md` | 要能打印的 PDF；要在屏幕上直接看懂的卡片 |

**磁盘布局（所有课同一套，路径由 `config.json` 决定）**：

```
{STUDY_DIR}\<课程名>\                     ← 课件 PDF / 教材 / _tools
<progress_dir>\<课程名>\进度.md            ← 进度表 + 课程档案（03-review.md）
<progress_dir>\<课程名>\能力评价.md        ← 掌握状态表（03-review.md）
<progress_dir>\<课程名>\题库.jsonl         ← 题目（09-local-store.md）
<progress_dir>\<课程名>\作答.jsonl         ← 作答记录，回测与能力评价靠它
<progress_dir>\<课程名>\排期.json          ← FSRS-6 排期
<progress_dir>\<课程名>\产出\              ← 课后题 / 试卷 / 章节总结 / 速查册 / 总总结（06-output.md）
```

`progress_dir` 默认是 `{STUDY_DIR}\学习进度`，相对路径相对 `study_dir`（见 `07-environment.md`）。新学科第一次进来走 `01-start.md` 的「零底座」段。

## 一、分流：手上是哪件活

**按用户原话找行，不要按自己的判断挑技能。** 插件自带几个 `study-*` 与 `good-learning` 都有「学一门课」的触发语，选错不会报错，只会少做摸底与回测。

| 用户说 / 手上的活 | 读哪篇 | 不归我的时候 |
|---|---|---|
| 从头学一门课、继续上次那门、建一门自学课 | `references/01-start.md` 开课 → `02-lesson.md` 逐讲 | 只要一个知识点当场测 → `study-tutor`；课件整理成册 → `study-intake` |
| 今天讲什么、讲完出题考我、带我学这章 | `references/02-lesson.md` | 同上 |
| 我学到哪了、周复盘、这门还差多少、回测 | `references/03-review.md` | — |
| 某概念在哪一页、要原文、新书 / 课件 / 照片进来 | `references/05-materials.md` | 只解析某一页取文本 → `doc-parsing` |
| 自己搭知识库、把教材入库、查页图 | `references/04-kb.md` | — |
| 出课后题 / 测试卷 / 知识清单 / 章节总结 / 速查册 | `references/06-output.md` | 写复习全书 → `study-book` |
| 有考试日或目标分数、排备考计划、估现在差多少 | `references/11-exam.md` | 定制一本大书只出考试范围 → `study-custom` |
| 讲解卡片糊了、字太小、深色主题下看不清 | `references/10-cards.md` | — |
| 路径怎么配、命令怎么跑、缺工具怎么退 | `references/07-environment.md` | — |
| 题目记在哪、到期怎么排 | `references/09-local-store.md` | — |
| 安装、分享、隐私、版本 | `references/08-sharing.md` | — |

拿不准就问自己「要不要摸底 + 排路线」：要完整链路走本技能，只做一件动作让给对应技能。踩过的坑在记忆库 lesson 层（`memory_search` 取），不放这里。

**两条起步提示**：第一次装 / 换机器 / 报依赖错 → `07-environment.md`，再跑 `scripts/check_env.py`；要自己搭一个能查页码的库 → `04-kb.md`（技能不带任何现成数据）。

## 二、完整链路

从「用户说要学这门」到「这课学完」，一步不跳。**第 0 步不是可选项**——五问没答就问后面的，问出来的是我猜的计划。

| 步 | 做什么 | 调谁 | 落在哪 |
|---|---|---|---|
| 0 五问 | 哪门课 / 为什么学（含「应付考试（要考期与真题）」）/ 资料状态 / 期限与投入 / 怎么摸底 | `01-start.md` 第一节 | 课程档案 |
| 1 定终点 | 按第 2 问四分叉 | `06-output.md` 清单格式 | 知识清单 |
| 2 摸底 | 6–8 题、四档、不打分；零底座课先做步 5 | 本会话出题 | 课程档案 |
| 3 画地图 | 清单八项（编号 / 名称 / 一句话 / 页码 / 依赖 / 难度 / 题型 / 易错） | `01-start.md` + `06-output.md` §四 | 知识清单 |
| 4 排路线 | 总讲数 → 分阶段 1–12 → 落成课程 | `01-start.md` 第三节 | 课程档案 |
| 5 导材料 | 教材 / 课件 / 录像进库（第 3 问决定走哪支） | `05-materials.md` | 本地路径 + 库内页码 |
| 6 写全书 | 每个知识点写一节，本会话直接写文件（不调插件） | `06-output.md` 第六节 | `复习全书\第NN章.md` |
| 7 带学 | 讲 → 出题 → 作答 → 看作答 → 再讲 | `02-lesson.md` | 题库 + 作答（`09-local-store.md`） |
| 8 巩固 | FSRS 复习 + 错题（`scripts\qbank.py due --course <课程>`） | `03-review.md` | 复习记录 |
| 9 交付 | 按第 2 问分叉 | `06-output.md` | `<progress_dir>\<课程名>\产出\` |
| 10 复盘 | 读进度表重排下周 | `03-review.md` 第四节 | 进度表 |

第一次走完整条链，就按这个顺序；**步 7 是循环**，每一讲回来一次，其余每步只做一次。改完脚本或文档跑一遍对账（见第六节）。

## 三、分篇索引

| 文件 | 管什么 |
|---|---|
| `references/01-start.md` | 开课五问、定终点、摸底、画地图、排路线、建课、零底座新课 |
| `references/02-lesson.md` | 每讲七步循环、时长分档、配示意图、带学动作与边界 |
| `references/03-review.md` | 进度表与能力评价、每 3 讲回测、周复盘、错题本、出题与复习 |
| `references/04-kb.md` | 建库通用流程：表结构、入库五步、三条验收（不含任何现成数据） |
| `references/05-materials.md` | 材料线与解析工具自选矩阵（PDF / 扫描 / PPT / 照片 / 录像） |
| `references/06-output.md` | 知识清单、备考计划、课后题 / 试卷 / 总结 / 速查册 PDF 契约 |
| `references/07-environment.md` | 路径与配置、命令速查、依赖自检与降级 |
| `references/08-sharing.md` | 安装三步、最小可用集、隐私、版本与许可 |
| `references/09-local-store.md` | 题库、作答与排期：字段、命令、排期规则、备份与边界 |
| `references/10-cards.md` | 卡片与图示的交付形态：底色字色、字号下限、SVG、交付前自检 |
| `references/11-exam.md` | 备考：目标模式与诊断问卷、计划五要素与五类时间、模拟与真题、找书判据 |

## 四、脚本索引

| 脚本 | 做什么 |
|---|---|
| `scripts/init.py` | 首次运行：问路径 → 写 `config.json` |
| `scripts/check_env.py` | 探测环境，输出「缺哪一档」 |
| `scripts/build_kb.py` | 建库最小实现：`--pdf`/`--dir` 入库、`--check` 验收检索、`--list` 列文档 |
| `scripts/qbank.py` | 本地题库：`init` / `exam` / `add` / `list` / `pick` / `grade` / `audit` / `due` / `stats` / `errors` / `export` / `backup` / `restore`；`add` 自带收题检查（`--strict` 拒绝写入、`--no-check` 跳过），`exam` 设考试日，`grade` 支持四档与四种「不算数」标记，`errors` 从作答记录生错题本 md |
| `scripts/render_study_pdf.py` | 章节总结 / 总总结 / 当天安排 / 错题纸 → `.tex`（四 kind：`knowledge` / `plan` / `day` / `errors`；前三种带封面与地图、固定 2 页起，`errors` 无封面无地图） |
| `scripts/render_quiz_pdf.py` | 课后题 / 试卷 → `.tex`，答案可另册 |
| `scripts/compile_study_pdf.py` | `.tex` → `.pdf`（XeLaTeX 实际编译） |
| `scripts/selftest.py` | 30 步端到端自检：临时目录里跑建课 → 加题 → 判分 → 设考试日 → 三种产物（另加计划与每日课两种 kind）→ 编译 → 两条负向，约 28 秒，不碰真实数据 |
| `scripts/doc_check.py` | 文档与脚本对账：文档里写的 `--参数` 在脚本 argparse 里存不存在、引用的文件在不在、`map-config` 覆盖不覆盖所有 kind |

## 五、铁律与禁区

两个系统都能做「学法、题目、错题、讲解」，同时用会打架。分界只有三条：

| 东西 | 放哪 | 为什么 |
|---|---|---|
| **数据**（题目 / 作答 / 排期 / 错题 / 课程阶段） | **只放本地**：`scripts/qbank.py` 的 `题库.jsonl` / `作答.jsonl` / `排期.json`（`09-local-store.md`） | 换个地方再记一份，两处都有状态与排期，必然分叉成两份真相 |
| **讲义与清单**（知识清单、备考计划、PDF、导图） | **走 `06-output.md`** | 本技能只出清单 / 计划 / PDF |
| **错题** | 唯一权威是题库；打印出来的错题 PDF 是快照 | 两本账会对不上，改的时候不知道该改哪本 |

计划也有两处写法：`01-start.md` 第三节的四项阶段表（建课用，1–12 个阶段）与 `06-output.md` 的六项学习计划（出 PDF 用）——**阶段划分以 01 为准**，06 只是把同一份计划补足成排版内容，不要各排一套。

禁区：

- 不要用任何库的 `rebuild` 做日常更新——`kb.py rebuild` 会先 DELETE 再重建索引，不是只重跑 OCR；日常入库走 `build_kb.py`（或等价脚本）的入库路径。
- 不要凭记忆报教材页码，一律查库。
- **不替别人写进度**：哪门课由哪个会话带，就由那个会话维护它的进度表。
- **不代答**：答案只归学习者本人；**判分分两类**——随堂题与回测由带学方判、按 again / hard / good / easy 四档给档位（不给分数）、只指出断在第几步，FSRS 复习由学习者自己对着答案自评。
- 不要在没有授权时发布草稿、删除或归档任何学习数据。
- 不要把 `.dsh-study`、`.dsh-mind`、插件缓存用 shell 搬动或删改。
- 五问答过不要重问（唯一例外：新课导完材料后回第 3 问）；也不要写死某一门课的名字。
- **产出跟随进度**：没讲完的章不出总结、不出速查册，没讲完的课不出总总结；不预生成。

## 六、自检

改完脚本或文档，跑两把尺子。**先定解释器**：本机裸 `python` 是应用商店占位程序（实测 exit=9009，报 `Python was not found; run without arguments to install from the Microsoft Store`），要用真正的那个——

```powershell
$PY = 'C:\deepseek\tools\sci-venv\Scripts\python.exe'   # 换机器就换成你自己的解释器
```

```powershell
& $PY scripts\selftest.py    # 全链 30 步，约 28 秒，不碰真实数据
& $PY scripts\doc_check.py   # 文档里写的参数是否真存在
```

两个都绿再交付——但记住这两个工具自己也会漏：`doc_check` 只验参数名不验必填，`selftest` 不覆盖它没写用例的新参数。环境出问题时看 `07-environment.md` 的降级表，哪一步退化就在那一步说一句，不假装正常。
