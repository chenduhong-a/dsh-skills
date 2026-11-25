# CHANGELOG

## 1.0.1 — 2026-11-26 · 命令不可执行、`--yes` 与备份的关系说反

三份技能诊断报告（`C:\deepseek\调研\技能梳理\`）里有三条经逐条复核为真，其中两条会让读者当场卡住：

- **占位符命令在 PowerShell 里根本跑不了**：全文的 `& <KB_PY> <KB_ROOT>\app\kb.py <子命令>` 写法，实测 `ParserError`——`<` 在 PowerShell 里是重定向运算符，`&` 后面接不了。同一份文档还有三种写法混用（`KB_ROOT`、`<KB_ROOT>`、`$KB_ROOT`），读者无法判断哪个是要替换的占位符。已统一为 `$KB_ROOT` / `$KB_PY` 两个 PowerShell 变量，并在 1 节给出可直接粘的赋值块：

  ```powershell
  $KB_ROOT = 'C:\deepseek\study\_kb'
  $KB_PY   = Join-Path $KB_ROOT 'py\Scripts\python.exe'
  & $KB_PY (Join-Path $KB_ROOT 'app\kb.py') status
  ```

- **`--yes` 与自动备份的关系写反了（最硬）**：原文说「加了 `--yes` 就没有这层保护，所以备份要自己先做」。实际 `kb.py:1372-1382` 的顺序是：建 `backup` 目录 → `shutil.copy2` 复制主库 → 打印「清库前已自动备份」→ **之后才** `if not args.yes: sys.exit(1)` → `rebuild(con)`。**加不加 `--yes` 都会先备份**，`--yes` 只跳过确认。已改正，并写清手动备份是「留一份库外副本/可回滚点」，不是因为这层保护被跳过。
- **两处硬编码计数过期**：`docs.meta` 实测从「36 行 / 3 行有值 / `pages: 456`」变为「37 行 / 4 行有值 / `pages: 510`」；`items.section` 从 260 个不同取值变为 262。都已更新并注明「行数会变，以 1 节的 count 查询为准」。

同时修的小问题：§4.5 的备份命令缺 `New-Item -ItemType Directory -Force`（新机器上 `backup\` 可能不存在，`Copy-Item` 会失败），已补。

未采纳：报告建议把「十二张业务表」拆成「10 应用 + 2 FTS 虚表 + 8 影子表」（口径问题不是错，优先级靠后）、新建 `references/schema.md`、补「新机器重建」六步、给 `kb.py` 加版本锚点。这些是结构补强，先挂账。
