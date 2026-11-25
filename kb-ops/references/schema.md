# 真实 schema（照记忆写 SQL 必踩空）

写任何 SQL 之前先跑 `pragma table_info(<表名>)`。这一篇记的是 2026-11-26 在 `C:\deepseek\study\_kb\kb.sqlite` 上实测的列名与几个反直觉的点。

## 12 张业务表 + 8 张 FTS 影子表

| 表 | 一行是什么 | 备注 |
|---|---|---|
| `docs` | 一篇文档 | **不存 PDF 本体**，只存路径与 sha256 |
| `items` | 一个知识条目（通常是 PDF 的一页） | 主体，绝大多数查询落在这 |
| `items_fts` | `items` 的 FTS5 索引 | external content 表，见下 |
| `cards` / `cards_fts` | 抽认卡 / 它的索引 | 1554 条量级 |
| `concepts` | 概念表 | 有 `doc_id` |
| `examples` | 例题表 | 有 `doc_id` |
| `files` | 磁盘文件登记 | `rebuild` 会**全清**它 |
| `vec` | 向量，一个 item 一行 | 见 4 节的向量坑 |
| `pagemap` | 书页码 → PDF 页序映射 | **长期近乎空**，别指望 |
| `courses` | 课程 | 5 门 |
| `review` | 复习记录 | 几乎没写者 |

另有 **8 张 FTS 影子表**（`*_fts_data` / `_idx` / `_docsize` / `_config`）——它们不算业务表，但排查索引时要数 `_docsize`。

## `docs` 的真实列

```
id  course_id  kind  rel_path  bytes  sha256  mtime  meta
```

**没有** `title`、**没有** `chapter_no`、**没有** `pages`、**没有** `source`。

- `select title from docs` → `sqlite3.OperationalError: no such column: title`。
- 章信息只在 `items.section`，不在 `docs`（详见 `section.md`）。
- `docs.meta` **多数是空字符串**：截至 2026-11-26 的 37 行里只有 4 行有值——两行是纯字符串 `文字层提取`，一行 `{"ocr": "mineru-local-standard", "pages": 510}`，一行高清版。**格式不统一**，解析要先试 `json.loads` 再兜底成字符串。**它不存章信息**，别指望。

## `items` 的真实列

```
id  doc_id  seq  title  section  asset  width  height  text  markdown  blocks
```

三个容易记错的：

- **页序叫 `seq`，不叫 `page`**。写 `where page = 36` 会报 `no such column`。
- **没有 `status` 列**。想看「这条有没有正文」只能判 `text` 是否为空串。
- `asset` / `width` / `height` 是图片型条目的字段；`blocks` 是原样的块结构 JSON，`find --block` 会用它过滤。

## `items_fts` 是 external content 表

建表语句形如 `CREATE VIRTUAL TABLE items_fts USING fts5(title, section, text, content='items', content_rowid='id', tokenize='trigram')`。

由此推出三件事：

1. **`count(*) from items_fts` 与 `items` 恒等**——索引失效了它也照样相等。**真计数看 `items_fts_docsize`**，或跑 `check --deep`。
2. **没有触发器**（实测 `sqlite_master` 里与 items 相关的 trigger 为 0 条）。改了 `items` 必须手动 `insert into items_fts(items_fts) values('rebuild')`，否则检索不到新内容。
3. **列序是 `(title, section, text)`**，不是 `(text, title, section)`。自己写 `fts5(...)` 对照时别抄反。

`cards_fts` 同理。

## 自查三条

```sql
-- 1) 各表行数（第一件事，不要信任何写死的数字，包括文档里的）
select 'docs', count(*) from docs
union all select 'items', count(*) from items
union all select 'cards', count(*) from cards
union all select 'vec', count(*) from vec;

-- 2) 索引真实行数
select count(*) from items_fts_docsize;

-- 3) 列名
pragma table_info(items);
```

**行数会变**，这一篇里出现的任何具体数字都只是「量级参考」，以查询结果为准。
