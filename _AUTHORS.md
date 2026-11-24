# 技能归属

> 2026-11-21 按用户口述建立。改技能前先看这里——**不是自己的一律不动**，除非用户明确要求。

## 归属

| 技能 | 归属 | 说明 |
|---|---|---|
| bili-transcript | **ZQY** | B站视频字幕与评论 |
| browser-skill | 插件自带 | 由 `browser-skill-dsh-plugin` 提供，升级会覆盖 |
| doc-parsing | **ZQY** | 文档解析复合技能：PDF 与扫描件篇 + Office 篇（2026-11-21 拆成 references 两篇） |
| dsh | **ZQY** | DSH 桌面版四合一手册 |
| good-learning | **非 ZQY** | 作者未注明；用户 2026-11-20 确认为「不是我写的」 |
| html-card | **ZQY** | 视觉卡片交付 |
| memory-collab | **ZQY** | 记忆维护与多代理协作 |
| shopping-guide | **ZQY** | 商品挑选方法 |
| skill-authoring | **ZQY** | 写 / 改 / 拆 / 验收技能的作者手册 |
| study-flow | **ZQY（LB 会话）** | author = `ZQY-LB`；LB 会话写并维护，**改前先问用户** |
| study-intake | **ZQY（LB 会话）** | author = `ZQY-LB`；LB 会话写并维护，**改前先问用户** |
| kb-ops | **ZQY（LB 会话）** | author = `ZQY-LB`；LB 会话写并维护，**改前先问用户** |
| thinking-discipline | **ZQY** | 思考纪律 |
| windows | **ZQY** | Windows 本机脚本防坑 |

## 自建插件

| 插件 | 归属 | 说明 |
|---|---|---|
| meow-mind | **ZQY** | 自研跨会话记忆插件，源码 `C:\deepseek\work\meow-mind` |
| dsh-doc-parser | **ZQY** | 源码 `C:\deepseek\tools\dsh-doc-parser`（`link:` 安装） |

## 不算「自建」的

`file:` / `link:` 安装但属于 fork 或上游的：

- `dsh-raw-html-v2`（`link:C:\deepseek\插件\dsh-raw-html-v2`）— 上游的视觉卡皮肤
- `dsh-plugin-structured-prompt`（`file:C:\deepseek\插件\forks\dsh-plugin-structured-prompt`）— fork

## 判据

改之前问一句：**这个技能 / 插件的作者是我吗？**

- author 以 `ZQY ·` 开头 → 是自己写的；**再看码**：码是本会话的可直接改；码是别的会话的（如 `LB-5E831608-0962`）**改前先问用户**——对方可能正在维护，用户要知道谁动了什么
- 没有 author 或署他人名 → **不是**，只读不写，把问题报给用户，让他转给维护者
- 不知道 → 先查 `grep` 与 mtime 佐证，仍不确定就问用户

## 改动的后果

`~/.agents/skills/` 不在插件体系内，**升级不会覆盖**，所以改坏没有回滚按钮——这也是「只改自己的」除了礼貌之外的第二个理由。
