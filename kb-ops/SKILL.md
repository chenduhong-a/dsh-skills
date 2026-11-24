---
author: "ZQY · LB-5E831608-0962"
name: kb-ops
description: "知识库运维手册——改库、修索引、重建 FTS、章节切分与卡片管理。当要读或改 kb.sqlite 的 items/cards/docs、跑 kb.py 子命令、重建 items_fts 或 cards_fts、给已有条目补 section、修章节切分与章号排序、清理白名单外的废弃文档、排查检索召回或向量索引失效时加载。管「库里的数据怎么动」，不管「文件怎么读成文本」（见 doc-parsing）、也不管「照片怎么整理成册入库」（见 study-intake）、更不管「怎么查教材原文」（见 study-flow 的 04-kb）。"
---

# 知识库运维

这个库不是黑盒：十二张业务表、一个 CLI、几条会静默出错的路径。运维的目标只有一个——**改完之后数据与索引同时正确**，而不是「命令返回 0」。

下文用两个符号，真实路径见文末「路径约定」：`KB_ROOT`＝库所在目录，`KB_PY`＝能跑这个库的 Python 解释器。

## 0. 先分清你在做哪件事

| 你要做 | 走哪节 |
|---|---|
| 查数据、翻条目 | 2 |
| 改正文 / 改标题 / 改 section | 3 |
| 索引坏了、召回为 0、报「为空」 | 4 |
| 章节切歪了、章号排序乱 | 5 |
| 清理废弃文档、删数据 | 3.4 |

**不归这里管**：把一个文件解析成文本（doc-parsing）、把一批照片整理成册再入库（study-intake）、按知识点查教材原文（study-flow 的 `references/04-kb.md`）。

## 1. 先摸清库在哪、有什么

`KB_ROOT` 下四样：`kb.sqlite`（主库）、`app\kb.py`（唯一 CLI 入口）、`py\Scripts\python.exe`（专用 venv，带 onnxruntime / pypdfium2 / python-pptx）、`models\`（向量模型，**运行依赖不是缓存**）。

跑任何命令都用 venv 的解释器：

```powershell
& <KB_PY> <KB_ROOT>\app\kb.py <子命令>
```

**第一件事是数一遍，不要信任何写死的行数**（包括本文档）：

```sql
select 'docs', count(*) from docs
union all select 'items', count(*) from items
union all select 'cards', count(*) from cards
union all select 'vec', count(*) from vec;
```

**第二件事是查索引真实行数**：`items_fts` 是 external content 表，`count(*) from items_fts` 与 `items` **恒等**，索引失效了它也照样相等。真计数看影子表 `items_fts_docsize`（`cards_fts_docsize` 同理），或直接跑 `kb.py check --deep`。

**第三件事是 `pragma table_info(<表名>)`**。照记忆写列名必踩空，`select title from docs` 直接报 `sqlite3.OperationalError: no such column: title`——`docs` 的真实列只有 `id / course_id / kind / rel_path / bytes / sha256 / mtime / meta`。

十二张业务表：`docs`（一篇文档一行）、`items`（知识条目，主体）、`items_fts`、`cards` / `cards_fts`、`concepts`、`examples`、`files`、`vec`（一 items 一行）、`pagemap`（长期近乎空，别指望）、`courses` / `review`；另 8 张 FTS 影子表（`*_fts_data` / `_idx` / `_docsize` / `_config`）。

`docs.meta` **多数是空字符串**，实测 36 行里只有 3 行有值（两行 `文字层提取`、一行 `{"ocr": "mineru", "pages": 456}`）——**不存章信息**，别指望它。

## 2. 读：查数据

高频子命令（`kb.py <cmd> -h` 看全参）：`find` / `page` / `card` / `cards` / `list` / `status` / `check` / `map` / `ask`。

**`find` 与裸 FTS MATCH 行为不同，别混**：

- `items_fts` 建表是 `tokenize='trigram'`（3 字成词）。**裸 `MATCH` 下 1–2 字必然 0 条**（实测 `MATCH '傅里'` 0 条、`MATCH '傅里叶'` 238 条）；
- 但 `kb.py find` 对 1–2 字会**自动走 LIKE 片段兜底**并提示「模糊匹配：没有精确包含「傅里」的条目……」——实测 `kb.py find 傅里` 命中 **40 条**，相关度很低。

所以「查不到」要分两种：走 `find` 却拿不到相关结果 → 说明 LIKE 兜底也没捞到像样的，换 3 字以上的词；自己写 SQL 用 `MATCH` → 先检查词长。

另两条：

1. **`page` 要两个位置参数：`doc` 和 `seq`**（usage 是 `page [-h] [--scale SCALE] [--out OUT] doc seq`）。只传一个直接报 `the following arguments are required: seq`。正确用法：`page 李正中 213`。
2. **没有 `stats` 子命令**（实测 `kb.py stats` 报 `invalid choice`）。查课程状态用 `status`，复习统计用 `review --stats`。

报「不存在 / 为空」之前，先跑一次 count：

```sql
select count(*) from items where doc_id = ?;
```

`find` 在 `--block` 时会按 `blocks` 过滤，`status` 的「有正文」统计会跳过 `text` 为空的条目——**命令报空 ≠ 表里没有**。`items` 表**没有 `status` 列**（真实列：`id / doc_id / seq / title / section / asset / width / height / text / markdown / blocks`）。

## 3. 写：改数据

### 3.1 改 items 之后必须重建 FTS

`items_fts` 是 **external content** 表（`content='items'`, `content_rowid='id'`），**没有触发器**（实测与 `items`/`items_fts`/`cards` 相关的 trigger 为 0 条）。所以：

```sql
update items set text = ? where id = ?;
insert into items_fts(items_fts) values('rebuild');   -- 不做这一步，检索不到新内容
```

`cards_fts` 同理。判断「要不要 rebuild」看 `sqlite_master` 里的建表语句与触发器列表，不看记忆。

### 3.2 改卡片要保 id

卡片按 `id` 定位，**不要整表重写**。改一条：`update cards set ... where id = ?` → 再 `rebuild cards_fts`。整表重写会让卡片 id 变，历史引用（笔记、复习记录、别的会话的指针）全断。

### 3.3 批量改先 dry run

改超过 5 条时，先只打印「将改哪些、每条改前改后各一句」，人眼过一遍再落库。判据按类型收窄（`section is null`、`doc_id = ?`），**别用关键词当唯一条件**。

### 3.4 清理要显式列白名单

删文档 / 删条目时，**白名单写法是显式列出要保留的核心数据文件与目录**，不是「排除 `*.sqlite`」。反例：按扩展名排除时把 `kb.sqlite` 之外的 `.json` 配置一起删了。

删之前先备份，备份命令与验收见 4.5。

## 4. 修：常见损坏与误判

### 4.1 `rebuild` 是清库重建，不是「按参数重建」

这是本技能最容易误伤的一条，先看清再动手：

```powershell
& <KB_PY> <KB_ROOT>\app\kb.py rebuild --help
# usage: kb.py rebuild [-h] [--yes]
#   --yes   确认清库重建（会丢正文）
```

**它没有任何「按参数重建」的选项**。函数体（`kb.py:619-630`）依次执行：

```
DELETE FROM files
DELETE FROM items WHERE doc_id IN (SELECT id FROM docs WHERE course_id IN (SELECT id FROM courses))
DELETE FROM docs
```

然后只重建「固体课件状态」与「PPT/幻灯片登记」两类，再把 `walk_files` 所列文件重新 upsert 进 `files`。**教材正文（PDF 抽出的 items）不在它重建的范围内**——跑完要重新 `extract` / `book` / `add` 才能回来。

两条护栏：

1. 不加 `--yes` 时脚本会**自动备份**到 `<KB_ROOT>\backup\kb.sqlite.auto-<YYYYmmdd-HHMMSS>`（`kb.py:1374`）；加了 `--yes` 就没有这层保护，所以**备份要自己先做**（见 4.5）。
2. **`rebuild` 不清 `vec` 与 `cards`**。跑完 `vec` 里那几千行会指向已删除的 items，变成孤儿——要么同时重建向量（`app\index_vec.py`），要么接受检索降级，并跑一次 `check --deep` 看对账结果。

同类：`book` 不只是重抽正文，**还会 `retitle` 把标题打回默认值**——补 section 或改标题之后别随手跑 `book`。

### 4.2 检索为 0 的三层排查（从便宜到贵）

1. **词长与通道**：自己写 SQL 用 `MATCH` → 1–2 字必 0（见 2 节）；用 `kb.py find` → 会走 LIKE 兜底，拿不到相关结果就换 3 字以上的词；
2. **索引与数据是否对得上**：比 `items` 与 `items_fts_docsize` 的行数（不是比 `items_fts`），或直接 `kb.py check --deep`；
3. **向量链路**：`vec` 行数齐 ≠ 可用，要 `onnxruntime` 能导入、模型在 `models\` 下。注意 **`find` 不打印任何分数**（只有课程/路径/页码/正文），所以「看首条相似度」这种验收做不到；能落地的检查是 `& <KB_PY> -c "import onnxruntime; print(onnxruntime.__version__)"`，以及 `kb.py check --deep` 里 vec 那一项。内部阈值 `VEC_MIN = 0.55`（`kb.py:919`），低于它的向量命中不进结果。

另外 `_fts_query` 里有一层 `except sqlite3.OperationalError: return []`——**FTS 语法写错会静默变成 0 条**，不报错。查不到又没有报错时，先把查询语句拿去直接 `MATCH` 试一遍。

### 4.3 换 venv 后 `--help` 全绿不代表能跑

19 个子命令的 `--help` 全过，第一条实际命令就 `ModuleNotFoundError: pypdfium2`。**换解释器后要把每个要用的子命令实执行一遍**，不能只看帮助。

### 4.4 依赖与缓存要分清

`models\` 下的向量模型（bge 系列）是**运行依赖**，删了检索直接挂，不是「缓存可以清」。真正可清的是 `_cache\`。

### 4.5 备份与验收（给可执行命令）

```powershell
$src = '<KB_ROOT>\kb.sqlite'
$dst = '<KB_ROOT>\backup\kb.sqlite.manual-{0:yyyyMMdd-HHmmss}' -f (Get-Date)
Copy-Item $src $dst
Test-Path $dst          # 必须 True，再报「备份好了」
```

验收不写「备份文件还在」，写**具体路径 + `Test-Path` 结果**。

## 5. 切：章节与章号

### 5.1 章节切分三步

1. **结构字段**：从 PDF 大纲 / 书签 / 标题样式取候选边界；
2. **正文校正**：候选边界与实际段落对齐，处理「标题在正文前 2–4 行」的情况；
3. **页码连续**：切出来的段落页码必须连续，出现倒退或跳跃说明边界错了。

三步都过才算切好。只做第一步会在「大纲只画到第一节」的书上切出一整本（群论 523 页实测）。

### 5.2 章号排序：章名在 `items.section`，格式不统一

`docs` 表**没有 `chapter_no` 列**。章信息只在 `items.section`，实测 260 个不同取值、四种书写混在一起：

```
第1章 抽象群理论        ← 书里的原生章名
群论 1.1                ← 课程 + 编号
§1.1.2 正方形的对称性群   ← 节号
§ 1.4 子群              ← 节号（§ 后有空格）
```

排序键三步，正则要写成可执行的（`N` 是占位符，直接抄会匹配不到）：

```python
import re
CN = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}
m1 = re.search(r'第\s*([0-9]+|[一二三四五六七八九十]+)\s*章', s)   # 第1章 / 第十二章
m2 = re.search(r'§\s*(\d+(?:\.\d+)*)', s)                        # §1.1.2 / § 1.4
```

优先级：先 `m1`（书原生章号），再 `m2`（节号），都没有按原序兜底。中文数字要提成整数再比——`第10章` 的 `U+0030` 小于 `第1–3章` 的 `U+2013 '–'`，字符串排序会把第 10 章排到前面。

### 5.3 书签三坑

- `/Prev /Next` 只连同父兄弟，用它们遍历会漏跨层节点；
- `pypdfium2` 读书签要处理「无标题 / 嵌套 / 指向页不存在」三种脏数据；
- 书签不可尽信：先试，再拿正文前 2–4 行校正。

## 6. 检索

### 6.1 换分词器不能靠 `rebuild`

`items_fts` 建表是 `CREATE VIRTUAL TABLE ... USING fts5(..., tokenize='trigram')`，带 `IF NOT EXISTS`；而 `rebuild()` 只执行 `INSERT INTO items_fts(items_fts) VALUES('rebuild')`，**既不 DROP 也不 CREATE**。所以：

- 想换分词器：必须显式 `DROP TABLE items_fts` → 用新 `tokenize` 重建 → 再把数据灌进去（不是 `rebuild` 子命令），且这一步会牵动 `items` 之外的东西，先备份；
- 只是内容变了：用 `INSERT ... VALUES('rebuild')` 重建索引即可，**别去跑 `kb.py rebuild`**（那是清库，见 4.1）。

同一个库里两个索引的分词方式必须一致，否则「写进去的」与「查出来的」是两套。

### 6.2 向量可用性的验收

不看表行数，看三样：`onnxruntime` 能导入、`models\` 下模型文件在、`check --deep` 里 vec 那项一致。**`find` 不打印相似度**，别在验收里写「看首条分数」。

## 停止条件

- 改完一行后 `count(*)` 没变 → **这不是判据**（`count(*)` 对 `update` 恒真）。要看 `select changes()` 或把目标行重新 `select` 出来比；
- `check` 报不一致且连跑两次报的不一样 → 停，先备份再查是不是并发写；
- 同一处改了两次仍不生效 → 停，回到 1 节重新 `pragma table_info`，别继续猜。

## 输出格式

改完报三样：**改了什么**（表名 + 行数）、**索引是否重建**（`items_fts` / `cards_fts` 各一行，附 `items_fts_docsize` 的行数）、**怎么验的**（跑的命令与读数）。三项缺一，就等于没改完。

## 验收

1. `select count(*) from items` 与 `select count(*) from items_fts_docsize` 一致（或说明差在哪几条、为什么）；
2. 改过的条目用 `find` 能查到（查询词**≥ 3 字**，或接受 LIKE 兜底的低相关度）；
3. `kb.py check --deep` 全绿——**默认的 `check` 只核 docs 文件 sha256，不核索引**；
4. 备份文件在，且能用 `Test-Path <具体路径>` 指出它；
5. 没有留下临时脚本与临时目录。

## 路径约定（本机固定值，换机器改这里）

| 符号 | 本机实际值 |
|---|---|
| `KB_ROOT` | `C:\deepseek\study\_kb` |
| `KB_PY` | `C:\deepseek\study\_kb\py\Scripts\python.exe` |
| 主库 | `C:\deepseek\study\_kb\kb.sqlite`（约 110 MB） |
| CLI | `C:\deepseek\study\_kb\app\kb.py` |
| 模型 | `C:\deepseek\study\_kb\models\` |
| 备份目录 | `C:\deepseek\study\_kb\backup\` |

`kb.py` 全部子命令（19 个，实测 `--help`）：`rebuild` / `extract` / `ocr` / `book` / `retitle` / `export` / `status` / `check` / `list` / `find` / `ask` / `cards` / `card` / `page` / `verify-text` / `review` / `map` / `add` / `ex`。**没有独立的向量检索子命令**，向量那条路只能通过 `find` 间接观察或用 `check --deep` 对账。
