# 依赖清单（kb-ops）

## 库根（`KB_ROOT`）

本机实例：`C:\deepseek\study\_kb`。正文里只用 `KB_ROOT` / `KB_PY` 两个符号，换机器改这一处即可。

| 项 | 路径 | 缺了会怎样 |
|---|---|---|
| 主库 | `<KB_ROOT>\kb.sqlite` | 一切免谈 |
| CLI 入口 | `<KB_ROOT>\app\kb.py`（19 个子命令，唯一入口） | 拿不到库 |
| 专用 venv | `<KB_ROOT>\py\Scripts\python.exe`（onnxruntime / pypdfium2 / python-pptx） | `kb.py` 起不来，别用系统 python 顶替 |
| 向量模型 | `<KB_ROOT>\models\`（bge-small-zh） | 见下面矩阵 |

## 缺 models 的降级矩阵

| 命令 | 缺 models 时 |
|---|---|
| `find` | **可用但静默降级**：不走向量，只剩 FTS / LIKE 片段兜底（1–2 字仍要换 3 字以上），不报错 |
| `page` / `cards` / `card` / `list` / `status` / `map` | 正常 |
| `ask` | **直接瘫**（靠向量召回组织答案） |
| `check --deep` | vec 那一项报红，其余正常 |

判据：先 `& <KB_PY> -c "import onnxruntime; print(onnxruntime.__version__)"`、再看 `models\` 在不在；两者任一不成立就按上表读结果，**别把「向量缺失」当成「库坏了」**。

## 边界

建库与入库不归本技能（`study-intake` 的 `kb_ingest.py`、`study-flow` 的 `references/04-kb.md`）；本技能只管库里数据与索引怎么动。
