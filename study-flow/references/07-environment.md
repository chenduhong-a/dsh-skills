# 07 · 环境、配置与降级

这一篇回答三个问题：**我该放哪、我用哪些工具、某样东西没有时怎么办。**

## 一、配置：`config.json`（先跑一次 `init`）

技能目录下的 `config.json`，第一次用时由 `scripts/init.py` 生成（**不要手写猜路径**）。示例见 `config.example.json`。

```json
{
  "study_dir": "D:\\study",
  "progress_dir": "D:\\study\\学习进度",
  "kb": { "enabled": false, "db": "", "cli": "" },
  "pdf_engine": "auto",
  "texlive_bin": "",
  "scripts_dir": "scripts"
}
```

| 键 | 含义 | 没有它怎么办 |
|---|---|---|
| `study_dir` | 课程资料根目录（教材、课件、成品 PDF） | 必填，`init` 会问 |
| `progress_dir` | 学习进度根目录（默认 `<study_dir>\学习进度`） | 用默认 |
| `kb.enabled` | 是否装了自有知识库 | `false` → 查原文改用 `doc_text` / `doc_render`（见本篇第五节） |
| `kb.db` / `kb.cli` | 知识库的 sqlite 与命令行入口 | `kb.enabled: false` 时留空 |
| `pdf_engine` | 解析引擎：`auto` / `doc_parser` / `mineru` / `none` | `auto` = 用到哪个试哪个。**注意：技能自带脚本目前没有一处读这个键**（`init.py` 只写默认值），PDF 解析能力靠运行时装包探测；这里只作人工记录 |
| `texlive_bin` | `xelatex` 所在目录。`init.py` 会自动探测 PATH 与 `~/texlive/<年>/bin/windows`、`C:/texlive/<年>/…`；探测不到就手填 |
| `scripts_dir` | 脚本目录（相对技能目录） | 用 `scripts` |

**判定优先级**：环境变量（`QBANK_PROGRESS` 这类覆盖口）> `config.json` > 内置默认。脚本一律从配置读路径，**不许把绝对路径写进脚本**。

## 二、环境自检（`scripts/check_env.py`）

一次打印「有什么、缺什么、缺了影响哪一步」。三类标记：`OK` 可用；`--` 没具备（缺了卡对应那一步）；`!!` 半可用或脚本测不到（需要在会话里实测一次）：

```
python          OK  3.12.14  C:\...\python.exe
config.json     OK  C:\...\study-flow\config.json
study_dir       OK  D:\study
progress_dir    OK  D:\study\学习进度
xelatex         OK  XeTeX 3.141592653-2.6-0.999998  ...\xelatex.exe
知识库           OK  D:\study\kb.sqlite，items 6258 条
py: pypdfium2   OK  可导入
py: pypdf       OK  可导入
py: fitz        --  未装（可选）
pdf 解析 / OCR   !!  脚本端不可用：会话里调 doc_info 一次
```

后两项标 `!!` 不是「缺」：**脚本没法替你调会话工具**，必须由会话里的老师实测一次并记住结果。退出码：**只有必需项失败才为 1**（python 版本不够、config 缺失或格式不对、目录不可写、xelatex 没找到）；`!!` 与可选包的 `--`（如上一行的 `py: fitz`）都不改变退出码，仍是 0。

判据：**哪一项缺，就在第一次用到它那一步说一句「因为缺 X，这一步改成 Y」，不要假装一切正常。**

## 三、依赖自检与降级

四档，按「缺了主链还走不走得动」排。**第 1 档缺了要改做法，第 2–4 档缺了只是少一样东西。**

**唯一没有降级路径的是 XeLaTeX**：试卷 / 总结 / 清单 / 错题纸都是 PDF，公式只有它排得出来。缺了不是「改个做法」，是这一步做不了——先装 TeX 再继续，别拿 md 或 HTML 顶。

### 1. 本地脚本与会话工具（缺了要改做法）

| 依赖 | 通过的样子 | 缺了改做什么 |
|---|---|---|
| 本地题库（`scripts\qbank.py`） | `scripts\qbank.py init --course X` 能建三份文件 | 退回「题写在正文 + 记录抄进进度表」，并说明自动排期停了 |
| 判分落库 | `scripts\qbank.py grade` 返回写入回执 | 说「这次作答没写进库」，同时抄进 `进度.md` 备注列 |
| 文档解析（`doc_*`） | `doc_info` 能出页数与文字层判断 | 见 `05-materials.md` 的备用路线：系统 PDF 库抽文本、关键页手抄 |
| 动态演示（`render_visual`） | 工具在，片段里的脚本会执行 | 只用静态图（手写 SVG、表格），不承诺「能点、能拖」 |
| 可编辑 Board（`univer_*`） | 能建 unit、能存 | 改用 SVG 或 Markdown 表，并说明「这份图不能再编辑」 |

### 2. 并列技能（不装不报错，只是那类请求没人接）

| 技能 | 它接什么 | 没装时本技能怎么办 |
|---|---|---|
| `good-learning` | 每日课程、错题本、备考计划 | 本技能只出清单 / 计划 / PDF；逐日讲解由会话自己排 |
| `study-intake` | 照片、PPT、扫描件整理成成品 PDF | 按 `05-materials.md` 的解析矩阵自己走一遍 |
| `study-custom` | 一本大书怎么定制、只要考试范围 | 直接按 `01-start.md` 开课五问，把范围写进终点 |

### 3. 系统层（装一次，长期用）

| 依赖 | 用途 | 缺了怎么办 | 去哪看 |
|---|---|---|---|
| Python 3.10+ | 跑 `scripts/` 全部脚本 | 脚本线全不可用，只剩手动流程 | `check_env.py` 第一行 |
| `pypdfium2` / `pypdf` | PDF 抽文本、切页、读页数 | 改用 `doc_*`，或手工抄关键页。**装过也会消失**：DSH 运行时升级会重置 site-packages，撞 `ImportError` 先按下节装法重装 | `py: pypdfium2` / `py: pypdf` |
| `fitz` | 渲染页图 | 可选，不影响主链 | `py: fitz` |
| XeLaTeX | 出 PDF 试卷 / 总结 / 清单 | **没有降级替代**：停在出产物这一步，先装 TeX（公式排不出来，md / HTML 顶替的产物没价值） | `xelatex` |
| 自建知识库（`build_kb.py` 建、`kb.py` 查） | 查教材原文与页码 | 用 `doc_text` 读页、`doc_render` 看原页（见第五节） | `build_kb.py --check 词1 词2 词3` |

装法：`& $PY -m pip install pypdfium2 pypdf`（国内可加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`）。**装完不是一劳永逸**——DSH 运行时升级会重置 site-packages，`pypdfium2` / `pypdf` 会静默消失（本机 `cv2` 已因此丢过两次）；`check_env.py` 的 `py:` 行变成 `--` 就是这个信号，重装即可，库文件与数据不受影响；XeLaTeX 装 TeX Live 或 MiKTeX，装完把 bin 目录填进 `config.json` 的 `texlive_bin`，或让 `init.py` 自动探测。

`QBANK_PROGRESS` 是**可选的覆盖口**，不设也能跑：它覆盖 `scripts\qbank.py` 的进度目录（默认读 `config.json` 的 `progress_dir`，主要给冒烟测试用）。知识库路径一律从 `config.json` 的 `kb.db` 读，没有第二个覆盖口。

### 4. 内核工具（不用另装，但要知道它们在）

`ask_user_question`（开课五问与拍板）、`read_image`（看照片课件）、`read` / `write` / `edit`（改进度表与脚本）。出题与判分都是同步的 `scripts\qbank.py` 命令，没有要等的后台任务。

**不要**在会话开头做一次统一体检然后宣布「环境 OK」——依赖会在中途变（判分失败要当场发现），所以**每个关键动作后读回执**；哪一项缺，就在第一次用到它那一步说一句「因为缺 X，这一步改成 Y」。

## 四、命令速查

| 要干什么 | 用什么 |
|---|---|
| 看这门课建好没有 | 打开 `学习进度\<课程名>\进度.md`；题库三件用 `scripts\qbank.py list --course X` |
| 存课程与学法 | 写 `进度.md` 的文件头与「## 路线」节（`01-start.md` 第三节） |
| 找题 / 加题 | `scripts\qbank.py pick --course X --n 5` · `scripts\qbank.py add --course X --prompt … --answer … --source …` |
| 写回作答 | `scripts\qbank.py grade --course X --qid q-0001 --grade good --confidence sure`（答错带 `--step 2`；`--confidence` 漏了返工判据就失效） |
| 复习 / 看答案 | `scripts\qbank.py due --course X` · `scripts\qbank.py pick --course X` · `scripts\qbank.py errors --course X`（错题本，默认落 `<课程>\错题本.md`） |
| 看资料原文 | `<KB_CLI> find "词"` · `<KB_CLI> page "<书名>" <PDF 页序>`（**不是书页码**，见 `05-materials.md`） · `doc_text`（`<KB_CLI>` 是使用者自配的查询 CLI，**必须写全路径**，没配就按 `04-kb.md` 第七节用 SQL 查） |
| 题库与排期 | `scripts\qbank.py init` / `exam` / `add` / `list` / `pick` / `grade` / `audit` / `due` / `stats` / `export` / `errors` / `backup` / `restore` |
| 设考试日（到期不越过它） | `scripts\qbank.py exam --course X --date 2026-12-26` |
| 这几种作答不算数 | `scripts\qbank.py grade ... --retry` / `--self-reported` / `--implicit` / `--simulated` |
| 题库导出给人看 | `scripts\qbank.py export --course X --out 题库.md` |
| 整课打包 / 换机器 | `scripts\qbank.py backup --course X` 出一个 zip（题库 / 作答 / 排期 / 进度 / 能力评价 + `_meta.json`），默认落 `<课程>\backup\<课程>-时间.zip`；`scripts\qbank.py restore --course X --src 备份` 整课替换（旧文件先转存到 `backup\pre-restore-<时间>\`，删到一半失败会把已删的放回原处） |
| 读 PDF 某一页的文字 | `doc_text`（有页范围） |
| 渲染 PDF 某一页成图 | `doc_render` |

## 五、没有知识库时怎么查原文

两个替代，按优先级：

1. **PDF 抽文本**：`doc_text --pages N-M` —— 拿到该页文字，够回答「书上怎么说的」。
2. **看原页**：`doc_render --pages N` 出图，自己读 —— 公式密集、抽取乱序时用这个。

## 六、脚本

| 脚本 | 用途 |
|---|---|
| `init.py` | 首次运行：问路径、写 `config.json`、建进度目录 |
| `check_env.py` | 打印环境自检表（本篇第二节） |
| `build_kb.py` | 从 PDF / 文本目录建最小知识库（`04-kb.md`） |
| `render_quiz_pdf.py` | 试卷 + 答案册 |
| `render_study_pdf.py` | 清单 / 计划 / 当天安排 / 错题本（`knowledge` / `plan` / `day` / `errors`；前三种配 `--map-config` 画路线图） |
| `compile_study_pdf.py` | 批量把 `.tex` 编成 PDF（失败排查加 `--keep-aux` 留日志） |
| `scripts\qbank.py` | 题库、作答、排期（13 个子命令，`09-local-store.md`） |
| `doc_check.py` | 对账：文档里写的脚本参数名与实际 argparse 是否一致 |
| `selftest.py` | 冒烟：临时目录里把十步法的主链跑一遍 |

调用一律 `& $PY <scripts_dir>\<脚本> <参数>`（`$PY` 怎么定见 `SKILL.md` 第六节，别在这里再写一遍裸 `python`）；脚本内部从 `config.json` 读路径。

## 七、附录：路径约定

```
<study_dir>\
  <课程名>\              课件、教材、成品 PDF、照片原件
  学习进度\
    <课程名>\
      进度.md            行程（03-review.md 第一节）
      能力评价.md        掌握（03-review.md 第二节）
      产出\              课后题 / 测试卷 / 总结（06-output.md）
```

- 一门课一个文件夹，**不要把所有课的进度挤进一个文件**。
- 一次性的中间文件放 `_tmp\`，用完删；不要散在课程目录根上。
- 目录名、文件名用中文没问题（脚本按 UTF-8 处理）。
