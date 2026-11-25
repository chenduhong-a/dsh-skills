# 命令手册：19 个子命令与它们的坑

`kb.py` 全部子命令（2026-11-26 实测 `--help` 的 `{}`）：

```
rebuild extract ocr book retitle export status check list
find ask cards card page verify-text review map add ex
```

**没有 `stats`**（`kb.py stats` 报 `invalid choice`）——查课程状态用 `status`，复习统计用 `review --stats`。**也没有独立的向量检索子命令**，向量那条路只能通过 `find` 间接观察，或用 `check --deep` 对账。

调用一律走 `$KB_PY`（见 SKILL 第 1 节的赋值块）：

```powershell
& $KB_PY (Join-Path $KB_ROOT 'app\kb.py') <子命令> [参数]
```

## 高频读命令

| 子命令 | 干什么 | 坑 |
|---|---|---|
| `find` | 全文 + 向量混合检索 | 见下两节，**1–2 字走 LIKE 兜底** |
| `page` | 渲染某一页成图 | **两个位置参数 `doc` `seq`** |
| `card` / `cards` | 查单张卡 / 列卡 | 乱词也会返回近似的卡，见「退出码」 |
| `list` | 列文档 | — |
| `status` | 课程与正文统计 | 「有正文」会跳过 `text` 为空的条目 |
| `check` | 核 docs 文件 sha256 | **默认不核索引**，要 `--deep` |
| `map` | 章节地图 | — |
| `ask` | 问答（**纯文本实现**） | 不走向量，见下 |

## `find` 与裸 `MATCH` 是两套行为

`items_fts` 建表是 `tokenize='trigram'`（3 字成词）。

- **裸 `MATCH` 下 1–2 字必然 0 条**：实测 `MATCH '傅里'` → 0 条，`MATCH '傅里叶'` → 238 条。
- **但 `kb.py find` 对 1–2 字会自动走 LIKE 片段兜底**，并提示「模糊匹配：没有精确包含「傅里」的条目……」——实测 `kb.py find 傅里` 命中 **40 条**，相关度很低。

所以「查不到」要分两种：

- 走 `find` 却拿不到相关结果 → LIKE 兜底也没捞到像样的，换 3 字以上的词；
- 自己写 SQL 用 `MATCH` → 先检查词长，1–2 字必然空。

另：`find` 在 `--block` 时会按 `blocks` 过滤；**`find` 不打印任何分数**（只有课程/路径/页码/正文），所以「看首条相似度」这种验收做不到。内部阈值 `VEC_MIN = 0.55`（`kb.py:919`），低于它的向量命中不进结果。

## `page` 要两个位置参数

usage 是 `page [-h] [--scale SCALE] [--out OUT] doc seq`。只传一个直接报 `the following arguments are required: seq`。

正确：`page 李正中 213`。

**第二个参数是 PDF 页序，不是书页码**——`kb.py:1263-1266` 是 `if not 1 <= seq <= total: …` 然后 `docobj[seq - 1].render(scale=scale)`。`pagemap` 表里有 `offset` 字段，但 `cmd_page` **不读它**。传书页码会静默渲染错页，不报错。

## `ask` 不走向量

`cmd_ask`（`kb.py:699` 起）是**纯文本**实现：全表扫 `items` / `cards` 做子串计数 + IDF + `ASK_SYNONYMS` + 最长前缀回退，**从不 import `embed`、从不读 `vec`**。

所以：「缺 `models\` 会让 `ask` 瘫掉」是**错的**——`ask` 在没有任何模型的情况下也能正常回答。会受影响的只有 `find` 的向量那一路（且它只降级不报错）。

## 索引与向量

- 改了 `items` / `cards` 之后要 `insert into <t>_fts(<t>_fts) values('rebuild')`，见 `rebuild.md`。
- **换分词器不能靠 `rebuild` 子命令**：`items_fts` 建表带 `IF NOT EXISTS`，`rebuild()` 只执行 `INSERT … VALUES('rebuild')`，**既不 DROP 也不 CREATE**。想换分词器必须显式 `DROP TABLE items_fts` → 用新 `tokenize` 重建 → 再灌数据，且先备份。
- 同一个库里两个索引的分词方式必须一致，否则「写进去的」与「查出来的」是两套。

## 退出码与「查不到」

- `find '傅里叶' --course '群论'` 没命中 → exit 2；
- 但 `find` 一个**纯胡话**（如 `'黎曼猜想xyz'`）反而可能命中一堆低相关条目、exit 0——LIKE 兜底与分词碎片都会捞到东西；
- `card '不存在的卡片'` 可能返回几张近似卡并 exit 0，换个更长的乱词才 exit 2。

**判据**：退出码只说明「有没有返回」，不说明「返回的对不对」。核内容对不对要自己看首条正文，或直接 `select` 出来比。

## 换 venv 之后

19 个子命令的 `--help` 全过，第一条实际命令就可能 `ModuleNotFoundError: pypdfium2`。**换解释器后要把每个要用的子命令真跑一遍**，不能只看帮助。

`models\` 下的向量模型（bge 系列）是**运行依赖**，删了 `find` 的向量路直接挂，不是「缓存可以清」。真正可清的是 `_cache\`。
