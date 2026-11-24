# study-flow · 从头系统学一门课

一套**不绑定具体课程**的带学流程：开课先问五件事，按答案分叉走完整条链，每一讲讲一个点、当场出题、当场批；每三讲一次跨章回测，每周一次复盘；课后题、测试卷、章节总结跟进度出文件。

它是给**会话里的「老师」**用的，不是给学习者读的——学习者只需要说「从头学一门课」「今天讲什么」「我学到哪了」。

## 快速开始

```powershell
# 0. 先定解释器（本机裸 python 是应用商店占位程序，敲了会 exit=9009）
$PY = 'C:\deepseek\tools\sci-venv\Scripts\python.exe'   # 换机器就换成你自己的解释器

# 1. 初始化（问三个问题：资料放哪、进度放哪、有没有知识库；编译器自动探测）
& $PY scripts\init.py

# 2. 自检（哪一项缺、缺了影响哪一步）
& $PY scripts\check_env.py
```

3. 在会话里说「从头学一门课」，按五问回答，然后跟着走。

**题库**：只有一套——`scripts/qbank.py`（两份 JSONL + 一份排期 JSON，FSRS-6 四档），不装任何插件也能跑，详见 `references/09-local-store.md`。题目与作答只存这一处。

想先看流程、不建真课：`assets/demo/` 有一份三讲小材料（Markdown，不需要 PDF），照 `references/08-sharing.md` 第三节走一遍即可；要用真实 PDF 练手，先装两个解析依赖 `& $PY -m pip install pypdfium2 pypdf`（不装也能手动抄材料，只是少了自动抽页）。

## 它长什么样

```
study-flow/
  SKILL.md              主入口：分流表、四层地图、三条铁律、十步法、禁区（~130 行）
  references/           按需读的细节
    01-start.md         开课：五问、摸底、地图、路线、建课
    02-lesson.md        每讲七步、带学动作、配示意图
    03-review.md        进度表、能力评价、回测、周复盘
    04-kb.md            建一个能查页码的知识库（通用流程）
    05-materials.md     材料：照片 / PPT / 扫描件 / 矢量 PDF 怎么进
    06-output.md        课后题、测试卷、总结；一律 PDF（无 Markdown 降级）
    07-environment.md   配置、自检、降级、命令速查
    08-sharing.md       依赖矩阵、安装、隐私、已知限制
    09-local-store.md   题库、作答与排期（纯文本，不依赖插件）
    10-cards.md         讲解卡片：底色字色、字号下限、SVG、交付前自检
  scripts/
    init.py             初始化配置
    check_env.py        环境自检
    build_kb.py         建最小知识库（SQLite + FTS5）
    scripts\qbank.py            本地题库 / 作答 / FSRS-6 排期（默认后端），含 add 的收题检查与 audit 体检
    render_quiz_pdf.py  试卷 + 答案册
    render_study_pdf.py 章节总结 / 总总结 / 当天安排 / 错题纸（四种 kind）
    compile_study_pdf.py 批量 .tex → PDF
    selftest.py         30 步端到端自检（临时目录，不碰真实数据）
    doc_check.py        文档里的参数与脚本 argparse 对账
  assets/
    progress-template.md / ability-template.md   进度与能力两张表的模板
    map-config.example.json                      依赖图配置示例
    demo/                                        三讲小材料（跑通用）
  config.example.json   配置模板（六个键的说明）
  config.json           ← init.py 生成，含本机路径，**不要提交或分享**
  CHANGELOG.md
```

## 核心设计（为什么这样排）

- **先猜再讲**：讲之前先让他猜一个答案，猜错也有用（生成效应）；讲完回到那道题说清差在哪。
- **讲完立刻出题、立刻停**：检索练习的价值在「先被问住」；不给停顿，讲得再清楚也留不下。
- **只指断点、不给分数**：批改说「断在第三步」，不说「70 分」——分数会让人停止思考。
- **示例淡出**：完整示例 → 半成品 → 独立做，新手先看完整解法比直接硬做有效。
- **每三讲跨章混抽 3 道**：间隔 + 交错，比每讲都考本讲内容记得牢；样本小，只作粗判。
- **两列记对错，不记正确率**：次数比比值更能看出趋势。
- **四种作答不算数**：重做、自述「会了」、从别的题推出来的、我演示的——混进去会让「稳」变成假象。
- **顽固题单独拎出来**：同一个点错 ≥3 次或近 5 次错 ≥60%，就换更少步骤的同源题，别再往上叠难题。

## 依赖

| 类别 | 装什么 | 缺了会怎样 |
|---|---|---|
| 硬 | 能读写文件的会话环境、Python 3.10+ | 跑不动 |
| 必须 | **本地 `scripts\qbank.py`**（两份 JSONL + 一份排期 JSON，FSRS-6 四档） | 缺了就退回「题写在正文、记录抄进度表」，自动排期停 |
| 软 | `doc_*` 解析、`render_visual`、`univer_*`、自建知识库 | 各有一档替代做法，不卡主链 |
| 出 PDF | **XeLaTeX + ctex 等宏包** | 没有降级路径：装不上就出不了 PDF（题仍可写在正文里） |
| 并列技能 | `good-learning`、`study-intake`、`study-custom`、`study-import` | 不报错，只是那类请求没人接 |

完整四档（含系统层与内核工具、逐项降级）见 `references/07-environment.md` 第三节。缺可选依赖时走降级路径，不会卡死，也不会假装有；XeLaTeX 那行是唯一的硬产出依赖，装不上就先把题写在正文里。

## 数据写在哪

```
<study_dir>\
  <课程名>\              课件、教材、成品 PDF
  学习进度\<课程名>\
      进度.md            行程
      能力评价.md        掌握
      产出\              课后题 / 测试卷 / 总结
      题库.jsonl         题目
      作答.jsonl         每次作答
      排期.json          到期日
```

不写系统目录、不改已有课程设置、不上传材料（除非你显式用在线 OCR）。

## 许可与致谢

流程设计参考了学习科学的主流结论：检索练习与分散练习（Dunlosky 等 2013）、测试效应（Roediger & Karpicke 2006）、交错练习（Rohrer 等 2019）、示例淡出与认知负荷（Sweller）、自我解释（Chi 等 1989）、预测试效应（Brod 等 2018）。

可自由修改自用；转载保留出处即可。
