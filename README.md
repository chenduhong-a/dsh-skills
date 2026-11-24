# dsh-skills

我在 [DeepSeek Harness](https://github.com/deepseek-ai) 里自建的技能（Agent Skill）集合，共 12 个。

每个技能是一个目录，入口是 `SKILL.md`；`references/` 是它按需展开的分篇，`evidence/` 是当时的实测记录，不读也不影响使用。

## 安装

克隆到你的技能目录（Windows）：

```powershell
git clone https://github.com/chenduhong-a/dsh-skills.git "$env:USERPROFILE\.agents\skills"
```

如果你已经有 `~/.agents/skills` 目录，别直接 clone 覆盖，改成分开拿：

```powershell
git clone https://github.com/chenduhong-a/dsh-skills.git "$env:TEMP\dsh-skills"
Copy-Item "$env:TEMP\dsh-skills\*" "$env:USERPROFILE\.agents\skills\" -Recurse -Force
```

重启 DSH 宿主，技能会出现在工具面里（`--only 06` 自检能看到这 12 个）。

## 三个必须知道的事

**1. 正文里的路径是作者机器的实例路径。** 你会看到大量 `C:\deepseek\...`、`C:\Users\ZQY\...`、`~\.dsh\...`——那是我的目录结构，**照抄在你机器上会失败**。判断方法看这些路径在句子里的角色：

- 讲「判据」的（例如「技能没出现先查它是否落在这六个根里」）与路径无关，可以直接用；
- 讲「具体文件在哪」的，换成你自己的路径。

**2. `author` 字段是归属标记，不影响使用。** 里面写着 `ZQY-LD` 或 `ZQY · LB-...`，表示这个技能是本机哪条线写的。想改就改，`SKILL.md` 只认 `name` 与 `description`。

**3. 有些技能依赖本机工具。** `kb-ops` 依赖 `kb.sqlite` 与本机的 `kb.py`，`bili-transcript` 依赖 B 站 MCP 与本地 ASR 环境，`dsh` 依赖本机的 DSH 安装与 profile。这些换了机器要自己补环境，照着技能里的「注意」节做。

## 这 12 个技能分别干什么

| 技能 | 什么时候用 |
|---|---|
| `bili-transcript` | 给 B 站链接要口播全文、画面、评论；字幕优先，没字幕走本地 ASR |
| `doc-parsing` | 读 PDF / 扫描件 / docx / pptx / xlsx：取文本、公式、表格、图片 |
| `dsh` | DSH 装升修卸、写插件、现场取证、十二项自检 |
| `html-card` | 做视觉卡片、图表、装帧页面；先判走哪个渲染器 |
| `kb-ops` | 改知识库、修索引、章节切分、卡片管理 |
| `memory-collab` | 写/改/合并/归档记忆，以及派子代理、切写域、跨会话交接 |
| `shopping-guide` | 挑商品、选型、比价；要方案不要清单 |
| `skill-authoring` | 写、改、拆、验收 Agent Skill 本身 |
| `study-flow` | 从头系统学一门课：开课、复习、出题、进度、备考 |
| `study-intake` | 把散落课件（翻拍照片 / ppt / 扫描 PDF）整理成册并入库 |
| `thinking-discipline` | 减少无效推理：一次定论、不猜就查、两次失败就停 |
| `windows` | Windows 本机写脚本、拼命令、查进程网络的防坑手册 |

## 许可

技能正文是我的实践记录，随取随用；其中引用的第三方内容（论文、仓库、文章）已在文中标出处，转载时请保留出处。
