# 09 · 题库、作答与排期

题目、作答与排期都由同目录的 `scripts/qbank.py` 管（下称 qbank），三份纯文本文件放在课程目录里，看得见、能改、能备份。**不依赖任何插件**，开箱就能用。

> 下面的命令都写成 `$PY scripts/qbank.py …`。`$PY` 是你的 Python 解释器，取法见 `SKILL.md` 第六节——**本机裸 `python` 是应用商店占位程序**（实测 exit=9009），直接敲跑不动。

没有第二个后端，也不需要开配置开关。题目与作答始终在这里。

## 一、数据放在哪

```
<progress_dir>/<课程名>/          # progress_dir 是相对路径时相对 study_dir；绝对路径直接用
   题库.jsonl     每题一行，只增不删（删题就手工删行）
   作答.jsonl     每次作答一行，只追加
   排期.json      qid -> {due, stability, difficulty, interval, reps, lapses}
               "_meta" 存课程级设置（目前只有考试日）
```

`progress_dir` 默认 `学习进度`；`QBANK_PROGRESS` 环境变量可临时覆盖根目录（测试用）。

## 二、三份文件的字段

### 题库.jsonl

| 字段 | 说明 |
|---|---|
| `id` | `q-0001` 起，自动编号 |
| `course` / `chapter` / `topic` | 课程、章、知识点三级，抽题按后两级过滤 |
| `kind` | `quiz`（选择/填空）、`open`（问答）、`task`（动手） |
| `prompt` | 题干 |
| `options` | 选项数组，没有就是 `null` |
| `answer` | 正确答案（`task` 类的留空写 rubric） |
| `rubric` | 评分标准，`open` / `task` 用 |
| `source` | 出处《书 p.N》或资料名，**必填可追溯** |
| `created` | 加入日期 |

### 作答.jsonl

| 字段 | 说明 |
|---|---|
| `qid` | 题号 |
| `ts` | `2026-11-18T22:20:00` |
| `correct` | true / false（`grade` 2–4 记 true，1 记 false） |
| `grade` | 1 again / 2 hard / 3 good / 4 easy |
| `step_break` | 断在第几步（题里有推导时填，没有就省略） |
| `confidence` | `sure` / `unsure`——答前标的那句 |
| `note` | 错因一句话 |
| `counted` | 是否计入掌握与排期；`false` 的一律不算 |
| `excluded_as` | 被排除的原因：`retry` / `self_reported` / `implicit` / `simulated`（可多个，逗号分隔） |

### 排期.json

每个 qid 一条：`due`（下次到期日）、`stability`（记忆稳定度，天）、`difficulty`（1–10）、`interval`（取整后的天数）、`reps`、`lapses`、`last`（上次作答日）。最近一次到期日被考试日截断时，另有 `unaligned_due` 记原始日期。

`"_meta"` 一条：`{"exam_date": "2026-12-26"}`，没设考试日就没有这个键。

## 三、命令

```powershell
$PY = 'C:\deepseek\tools\sci-venv\Scripts\python.exe'   # 换机器就换成你自己的解释器

# 建目录
& $PY scripts\qbank.py init --course demo

# 加题（选项用 | 分隔；写完会跑一遍收题检查，见本节末）
& $PY scripts\qbank.py add --course demo --chapter 第1讲 --topic 极限的定义 `
   --prompt "势阱里的驻波条件是什么？" --options "kL=nπ|kL=2nπ|k=nL" --answer A `
   --source "高量9 p5"

# 收题检查（add 时自动跑；这一条是单独体检全库）
& $PY scripts\qbank.py audit --course demo

# 抽题：到期优先，其次新题，最后没到期的
& $PY scripts\qbank.py pick --course demo --n 3 --chapter 第1讲

# 设考试日（排期不会外推到这一天之后；到期早于考试日的不受影响）
& $PY scripts\qbank.py exam --course demo --date 2026-12-26

# 记一次作答（四档给分；--step 记断点，--confidence 记信心）
& $PY scripts\qbank.py grade --course demo --qid q-0001 --grade good --confidence sure
& $PY scripts\qbank.py grade --course demo --qid q-0002 --grade again --step 2 --note "把边界条件当成结果"
& $PY scripts\qbank.py grade --course demo --qid q-0003 --grade hard   # 提示一句后才想起来
& $PY scripts\qbank.py grade --course demo --qid q-0004 --grade easy   # 秒答，且说得清为什么

# --correct / --wrong 仍可用，分别等价 --grade good / --grade again

# 四种「不算数」的作答：只记痕迹，不动排期、不进掌握
& $PY scripts\qbank.py grade --course demo --qid q-0001 --wrong --retry
& $PY scripts\qbank.py grade --course demo --qid q-0002 --correct --self-reported
& $PY scripts\qbank.py grade --course demo --qid q-0003 --correct --implicit
& $PY scripts\qbank.py grade --course demo --qid q-0001 --correct --simulated

# 今天到期什么
& $PY scripts\qbank.py due --course demo

# 题量 / 正确率 / 最弱知识点
& $PY scripts\qbank.py stats --course demo

# 导成 Markdown（打印或给学生看）
& $PY scripts\qbank.py export --course demo --out 题库.md
```

> `--out` 与 `--db` 都**相对当前工作目录**解析：从技能目录里跑会把产物写进技能目录。写绝对路径，或先 `cd` 到课程目录。

### 收题检查（能自动判的五条）

`add` 写完就跑一遍，逐条打印；`--strict` 时有提示就拒绝写入，`--no-check` 整段跳过。`audit` 是同一个检查批量跑全库，有提示时退出码 1。

| 自动查 | 判据 | 为什么 |
|---|---|---|
| 题干自足 | 没有「如上图 / 如图 / 由上可知 / 同上题」这类指代 | 配图丢了或换人看就答不了 |
| 有答案 | `--answer` 非空 | 判分时无从对照 |
| 有出处 | `--source` 非空 | 以后核对不了，也说不清考的哪一段 |
| 选项像样 | 选择题至少两个、不重复 | 一个选项等于没得排除 |
| 不是重题 | 与已有题的前 40 个非空白字符相同 | 同一道题记两次会污染排期 |

**自动查不了的两条**，仍然靠人：①考的是要点不是边角；②解释说得通、能一步步讲清。这两条写在 `02-lesson.md` 的「收题六问」里，出题时自己过。

## 四、排期规则

就是 FSRS-6：与常见的 ts-fsrs 实现用同一组 21 个权重、同一条遗忘曲线。差别只剩两处——不做短期记忆步骤、不做随机抖动（那些实现通常也把这两项关着），所以同一串作答算出来的间隔天数应当一致。

四档评分：**随堂题与回测由带学方判**（不换算成百分制）；FSRS 复习那一步由学习者对着答案自评（`03-review.md` 第六节）。

| 档 | 什么时候给 | 编号 |
|---|---|---|
| again | 答错，或卡住说不出下一步 | 1 |
| hard | 提示一句之后才想起来 | 2 |
| good | 独立做对 | 3 |
| easy | 秒答，且能说清为什么 | 4 |

| 情况 | 怎么算 |
|---|---|
| 遗忘曲线 | `R = (1 + 0.9803 × t / S) ^ −0.1542`（`t` 是距上次作答的整天数） |
| 首次 | `S = w[g−1]`：0.21 / 1.29 / 2.31 / 8.30 天；`D = w4 − e^(w5·(g−1)) + 1`，夹在 1–10 |
| 之后答对（g≥2） | `S' = S × (1 + e^1.87 × (11−D) × S^−0.167 × (e^(0.796(1−R)) − 1) × hard × easy)`；`hard` 只在 g=2 时乘 `0.60`，`easy` 只在 g=4 时乘 `1.87` |
| 之后答错（g=1） | `S' = min(S, 1.48 × D^−0.061 × ((S+1)^0.263 − 1) × e^(1.65(1−R)))` |
| 难度更新 | `D' = D − 3.02 × (g−3) × (10−D)/9`，再向 `D0(4)=1` 回归 `w7=0.001` |
| 下次间隔 | `clamp(round(S'), 1, 36500)` 天 |

三条由此而来、必须知道的行为：

- **越难的题排得越密**：`D` 现在跟着作答走——答错推高、`easy` 压低，常错的题间隔涨得慢。
- **同一天重复作答不增长**：`t = 0` 时 `R = 1`，括号里 `e^0 − 1 = 0`，`S` 原地不动。想拉间隔就隔天再来，别一天刷十遍。
- **考试日只压到期日**：间隔够到考试就排到考试日，`interval` 本身不放水（原始日期存 `unaligned_due`）。

判据：单机自学、题量几百道以内，这套和 ts-fsrs 标准实现算出来的天数一致。

## 五、备份与清理

- 三份都是纯文本：直接复制整个 `<课程名>` 目录就是完整备份；建议每两周一次。
- 开学新课时 `init` 一次，不要把不同课程混进同一个目录。
- 删题：手工删 `题库.jsonl` 里那一行，同时删 `排期.json` 里对应键（否则 `due` 会放出「题库里已删」的占位行）。

## 六、边界

- 题库里只放**有出处**的题；现编的题标 `source: "现编，未入库"` 并事后补录。
- 不把题干、答案抄进 `进度.md` 或记忆库——那里只记「哪个知识点、对错、断在第几步」的摘要。
- `scripts\qbank.py` 不打分（只记四档档位与断在第几步），与能力评价的口径一致。
