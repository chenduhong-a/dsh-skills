# `rebuild` 的破坏面与安全重建

> 从 `SKILL.md` §4.1 拆出。**动手前必读这一篇。**
> 依据：`_kb\app\kb.py:619-630`（`rebuild()`）、`:1372-1382`（自动备份）、2026-11-26 在副本库上的实测。

## 一、它到底删什么

```powershell
& $KB_PY (Join-Path $KB_ROOT 'app\kb.py') rebuild --help
# usage: kb.py rebuild [-h] [--yes]
#   --yes   确认清库重建（会丢正文）
```

**没有任何「按参数重建」的选项**。函数体依次执行：

```
DELETE FROM files
DELETE FROM items WHERE doc_id IN (SELECT id FROM docs WHERE course_id IN (SELECT id FROM courses))
DELETE FROM docs
```

然后只重建「固体课件状态」与「PPT/幻灯片登记」两类，再把 `walk_files` 所列文件重新 upsert 进 `files`。

**教材正文（PDF 抽出的 items）不在它重建的范围内**——跑完要重新 `extract` / `book` / `add` 才能回来。

## 二、破坏面有多大（2026-11-26 在副本库上真跑过）

| 表 | 跑前 | 跑后 | 说明 |
|---|---:|---:|---|
| `docs` | 37 | **261** | `walk_files` 把磁盘上每份 PDF 都登记回去 |
| `items` | 6422 | **510** | 27 篇教材的 **5912 条正文消失** |

PPT 那 209 条会由 `extract` 自动回来，**PDF 那 6213 条不会**。

## 三、日常修索引不要用它

```powershell
& $KB_PY (Join-Path $KB_ROOT 'app\kb.py') check --deep       # 先看哪里不一致
& $KB_PY (Join-Path $KB_ROOT 'app\kb.py') ex --rebuild-fts   # 只重建 FTS，不动数据
```

`rebuild` 是「把库推倒重来」的工具，不是修索引的日常工具。

## 四、两条护栏

1. **加不加 `--yes` 都会先自动备份**到 `$KB_ROOT\backup\kb.sqlite.auto-<YYYYmmdd-HHMMSS>`。`kb.py:1372-1382` 的实际顺序是：建 `backup` 目录 → `shutil.copy2` 复制主库 → 打印「清库前已自动备份」→ **之后才** `if not args.yes: sys.exit(1)` → `rebuild(con)`。所以 `--yes` 只跳过确认，**不跳过备份**。
   - 本机 `_kb\backup` 里**没有一条 `kb.sqlite.auto-*`**，说明 `rebuild` 在本机从没被真跑过——这层保护也就从没被验证过。
2. **`rebuild` 不清 `vec` 与 `cards`**。跑完 `vec` 里那几千行会指向已删除的 items，变成孤儿——要么同时重建向量（`app\index_vec.py`），要么接受检索降级，并跑一次 `check --deep` 看对账结果。

## 五、第二条不能碰的：不要 `DELETE FROM docs`

`docs.id` 是 `INTEGER PRIMARY KEY`（**没有 AUTOINCREMENT**），清空后新插入的文档会从 1 重新分配 id。

而 `cards`(1554) / `concepts`(849) / `examples`(2295) / `pagemap`(9) 四张表都有 `doc_id`，`rebuild` 不清它们 —— 清完 docs 再插，这四张表的 `doc_id` 全部指到别的书上。

**`check --deep` 只查行数一致性，这种错它照样打印「三方一致」。**

## 六、删单篇文档的正确六步

```sql
DELETE FROM vec      WHERE item_id IN (SELECT id FROM items WHERE doc_id = ?);
DELETE FROM items    WHERE doc_id = ?;
DELETE FROM cards    WHERE doc_id = ?;
DELETE FROM concepts WHERE doc_id = ?;
DELETE FROM examples WHERE doc_id = ?;
DELETE FROM docs     WHERE id = ?;
-- 最后：<KB_CLI> ex --rebuild-fts
```

一步不能少：只删 `items` 会留下指向空 id 的 cards；只删 `docs` 会让 id 重排。

## 七、同类：`book` 也会改标题

`book` 不只是重抽正文，**还会 `retitle` 把标题打回默认值**——补 section 或改标题之后别随手跑 `book`。

## 八、动手前的检查表

- [ ] 我要的是「修索引」还是「推倒重来」？前者用 `check --deep` + `ex --rebuild-fts`，不用 `rebuild`
- [ ] 库备份过没有？（备份要用 SQLite 在线备份，见 `SKILL.md` §4.5，别直接 `Copy-Item`）
- [ ] 我会不会在 `rebuild` 之后重建向量？不重建的话 `vec` 里会有几千行孤儿
- [ ] 我有没有在任何地方 `DELETE FROM docs`？有的话，四张关联表都要一起清
