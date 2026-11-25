---
author: "ZQY-LB"
name: kb-ops
description: "知识库运维手册——改库、修索引、重建 FTS、章节切分与卡片管理。当要读或改 kb.sqlite 的 items/cards/docs、跑 kb.py 子命令、重建 items_fts 或 cards_fts、给已有条目补 section、修章节切分与章号排序、清理白名单外的废弃文档、排查检索召回或向量索引失效时加载。管「库里的数据怎么动」，不管「文件怎么读成文本」（见 doc-parsing）、也不管「照片怎么整理成册入库」（见 study-intake）、更不管「怎么查教材原文」（见 study-flow 的 04-kb）。"
---

# 知识库运维

这个库不是黑盒：12 张业务表、一个 CLI、几条会静默出错的路径。运维的目标只有一个——**改完之后数据与索引同时正确**，而不是「命令返回 0」。

下文用两个 **PowerShell 变量**（不是占位符，可直接粘）：

```powershell
$KB_ROOT = 'C:\deepseek\study\_kb'
$KB_PY   = Join-Path $KB_ROOT 'py\Scripts\python.exe'
& $KB_PY (Join-Path $KB_ROOT 'app\kb.py') status
```

> 早先这里写的是 `& <KB_PY> <KB_ROOT>\app\kb.py`——**尖括号在 PowerShell 里是重定向符，那行根本跑不了**（2026-11-26 实测 ParserError）。

## 0. 先分清你在做哪件事

| 你要做 | 读哪篇 |
|---|---|
| 查数据、翻条目、跑子命令 | `references/commands.md` |
| 弄清列名、表结构、为什么 `count` 对不上 | `references/schema.md` |
| 索引坏了、召回为 0、`rebuild` 能不能跑 | `references/rebuild.md` |
| 章节切歪了、章号排序乱、书签读错 | `references/section.md` |
| 改正文 / 改标题 / 补 section | 本文件 §2 |
| 清理废弃文档、删数据 | 本文件 §3 |

**不归这里管**：把文件解析成文本（doc-parsing）、照片整理成册再入库（study-intake）、按知识点查教材原文（study-flow 的 `04-kb.md`）。

## 1. 动手前先数三样

```sql
-- ① 各表行数（不要信任何写死的数字，包括本文档）
select 'docs', count(*) from docs
union all select 'items', count(*) from items
union all select 'vec', count(*) from vec;

-- ② 索引真实行数（items_fts 是 external content，count 与 items 恒等，看不出来）
select count(*) from items_fts_docsize;

-- ③ 列名（照记忆写 SQL 必踩空）
pragma table_info(items);
```

`KB_ROOT` 下四样：`kb.sqlite`（主库）、`app\kb.py`（唯一 CLI）、`py\Scripts\python.exe`（专用 venv）、`models\`（向量模型，**运行依赖不是缓存**）。

> **缺 `models\` 会怎样**：`find` 的向量那一路静默降级（只剩 FTS/LIKE，不报错）；`ask` **不受影响**——它是纯文本实现，从不读 `vec`。完整矩阵见 `DEPENDENCIES.md`。

## 2. 写：改数据

**改完必须重建索引**。`items_fts` / `cards_fts` 是 external content 表，**没有触发器**，改了数据不 rebuild 就检索不到：

```sql
update items set text = ? where id = ?;
insert into items_fts(items_fts) values('rebuild');
```

三条规矩：

1. **改卡片要保 id**。卡片按 `id` 定位，`update cards set … where id = ?` 后重建 `cards_fts`。整表重写会让 id 变，历史引用全断。
2. **批量改先 dry run**。超过 5 条时先只打印「将改哪些、改前改后各一句」，人眼过一遍再落库。判据按类型收窄（`section is null`、`doc_id = ?`），**别用关键词当唯一条件**。
3. **改一行后 `count(*)` 没变不是判据**（对 `update` 恒真）。要看 `select changes()` 或把目标行重新 `select` 出来比。

## 3. 删：白名单 + 先备份

**白名单写法是显式列出要保留的核心数据与目录**，不是「排除 `*.sqlite`」。反例：按扩展名排除时把配置 `.json` 一起删了。

**先列清单再动手**——库里占多数的不是课件，是教材（27 篇 / 5912 条），删错一门课先没的就是它们：

```sql
SELECT d.id, d.course_id, d.kind, d.rel_path, count(i.id) AS items
FROM docs d LEFT JOIN items i ON i.doc_id = d.id
GROUP BY d.id ORDER BY d.course_id, d.kind;
```

**删单篇文档要按 `rebuild.md` 里那六步走，不要单独 `DELETE FROM docs`**——`docs.id` 无 AUTOINCREMENT，清空后从 1 重排，而 `cards` / `concepts` / `examples` / `pagemap` 的 `doc_id` 会指到别的书上；`check --deep` 只查行数，这种错它照样打印「三方一致」。

### 备份（WAL 模式，不能用 `Copy-Item`）

```powershell
$src = Join-Path $KB_ROOT 'kb.sqlite'
$dst = Join-Path $KB_ROOT ('backup\kb.sqlite.manual-{0:yyyyMMdd-HHmmss}' -f (Get-Date))
New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null   # 新机器上 backup\ 可能还不存在
# 不要 Copy-Item 直接拷：库在 WAL 模式，-wal 里还有没落盘的事务，只拷主库可能是缺最后几笔写入的库。
# 用 SQLite 自己的在线备份，它会把 WAL 合进去。
& $KB_PY -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" $src $dst
Test-Path $dst          # 必须 True，再报「备份好了」
```

验收写**具体路径 + `Test-Path` 结果**，再补一句行数对账（`select count(*) from items` 两边应一致）。

> **备份文件的 mtime 不可信**——`copy2` 与 `Copy-Item` 都保留源文件时间，`manual-20261125-213916` 的修改时间显示的是 11-19。**按文件名里的时间戳排序**，不要按修改时间挑。

## 停止条件

- `check` 连跑两次报的不一样 → 停，先备份再查是不是并发写；
- 同一处改了两次仍不生效 → 停，回到 §1 重新 `pragma table_info`，别继续猜；
- 要跑 `rebuild` 之前 → 停，读完 `references/rebuild.md` 的破坏面再决定。

## 验收

1. `select count(*) from items` 与 `select count(*) from items_fts_docsize` 一致（或说明差在哪几条、为什么）；
2. 改过的条目用 `find` 能查到（查询词 **≥3 字**，或接受 LIKE 兜底的低相关度）；
3. `kb.py check --deep` 全绿——**默认的 `check` 只核 docs 文件 sha256，不核索引**；
4. 备份文件在，且能 `Test-Path` 指出它；
5. 没留下临时脚本与临时目录。

## 输出格式

改完报三样：**改了什么**（表名 + 行数）、**索引是否重建**（附 `items_fts_docsize` 的行数）、**怎么验的**（命令与读数）。三项缺一就等于没改完。

## 路径约定（本机固定值，换机器改这里）

| 符号 | 本机实际值 |
|---|---|
| `KB_ROOT` | `C:\deepseek\study\_kb` |
| `KB_PY` | `C:\deepseek\study\_kb\py\Scripts\python.exe` |
| 主库 | `C:\deepseek\study\_kb\kb.sqlite`（约 110 MB） |
| CLI | `C:\deepseek\study\_kb\app\kb.py` |
| 模型 | `C:\deepseek\study\_kb\models\` |
| 备份目录 | `C:\deepseek\study\_kb\backup\` |
