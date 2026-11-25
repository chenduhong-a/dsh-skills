---
name: dsh-ops-playbook
description: DSH 桌面版的装、升、修、卸操作手册——插件怎么过门控、升级后怎么验收、工具消失怎么排查、内核更新失败怎么善后、版本怎么判真伪、带补丁的包怎么升、卸载怎么清残留。装插件 / 升级 / 卸载 / 工具不见了 / 更新失败 / 面板提示新版时加载；这是操作流程，不是体检清单。
---

# DSH 运维手册（判据篇）

> 场景：装东西、升东西、东西坏了、要卸东西。**每次都要先拿到用户明确同意再动手**，给完方案再执行。
> 本文件只放「怎么做 + 怎么判 + 什么不许」；带日期的实测记录、事故叙事、字节数与报错原文在 `evidence/ops.md`，**执行时不必读**，只在查判据来源时按节号查。
> 新旧冲突处写成「旧结论 → 现结论」；没标日期的即现行判据。
> 路径口径：`DSH_HOME`＝`C:\Users\ZQY\.dsh`（换机器即 `%USERPROFILE%\.dsh`），`profiles\desktop` 即 `DSH_HOME\profiles\desktop`；下文的 `<profile>` 默认写 `desktop`。

## 0. 动手前的五件事

1. **问**：装什么、升什么、改什么、卸什么，先说清代价（体积、是否需重启、会不会丢本地补丁），等用户点头。**用户回答「要不要装」这类选型问题 ≠ 批准**。
2. **备份**：`C:\deepseek\work\handover\backups\<事情>-<YYYYMMDD>\` 至少存 `profiles\desktop\package.json` 与 `cordis.patch.yml`；升内核再加一份 `bundles-before.txt` 并留好当前安装包——桌面内核没有回滚按钮，回退只能重装。
3. **改三方插件要四件套**：改动落 `profiles\desktop\node_modules\<pkg>`（升级会覆盖）→ 生成可重放补丁存 `C:\deepseek\插件\patches\<pkg>-<ver>-<要点>.patch` → 双向验证（原始+补丁 SHA256 == 实装，且 `git apply -R --check` 通过）→ 在 `C:\deepseek\插件\插件说明.txt` 记一笔。
4. **同日小版本合并**（省一次重启）：若某版本**已装但从未被运行实例加载过**（最后一次 `[desktop] starting` 之前已装、且没做过运行态取证），而更新面板又报了更新的版本，就直接把 vendor/npm 顶到最新再重启；依据不足就老实分两次装、两次验。
5. **CLI 参数作用域**：`dsh <profile> [app-args]`——`--port` / `--no-open` / `--json` 都是**被启动 app 的参数**，必须写 `dsh bp2 --port 0`；写成 `dsh --profile bp2 --port 0` 会被 launcher 当未知选项，报 `unknown option '--port'`。查某 profile 实际 app 的参数用 `dsh <profile> --help`。

依据见 evidence/ops.md 第 0 节

## 1. 门控四层（判断能不能装）

**R1：安装前先过门控**——核对插件要求的内核版本、peer 依赖与服务依赖；**先分清「声明的保守门禁」与「真不兼容」**：peer 版本号不满足但代码零引用 → 可装（0.2.2 起只 WARN，见 1.2）；引用了内核已删的符号才停手，停手要说明缺什么、有没有替代包。四层：①**peer 严格语义比对**（含内核线 `^0.2.2-rc.1` 这类；作者常用 `<x.y.z-0` 挡住未验证的下一版线，那是保守 house rule，≠ 真不兼容）；②**host inject 服务存在性**——回源码 `grep "provide("` 为准，Cordis Inspect 的 Service 目录只是精选契约表，**没列出 ≠ 不存在**；③**client.inject 包存在性**；④**符号级比对**（插件 `import` 的符号 vs 内核真实导出）。
**判据：声明缺失但代码里零引用＝降级可装**——必须解包 grep 代码级引用，不能只看声明。

**命令约定（先看这条，后面所有命令都按它）**：本文的 `dsh` 指 `$deploy\resources\runtime\cli\bin\dsh.cmd`（`$deploy` ＝ 程序本体目录，即 `SKILL.md` 路径表的 `DEPLOY_DIR`）。本机照抄前先建两个变量：

```powershell
$deploy  = 'C:\deepseek\官方'                                   # 换机器改这里
$profile = "$env:USERPROFILE\.dsh\profiles\desktop"              # 换 profile 改这里
$dsh     = "$deploy\resources\runtime\cli\bin\dsh.cmd"
```

**不写 `--profile` 时用默认 profile**（本机是 `desktop`），脚本里一律显式写 `--profile desktop`。

**四层怎么执行（都能照抄）**——先把 tarball 解包到临时目录（`npm pack <pkg>@<ver>` 或直接下 `https://registry.npmjs.org/<name>/-/<name>-<ver>.tgz` 后 `tar -xzf`）：
- **① peer**：`npm view <pkg> peerDependencies` + `& $dsh --version`，用 semver 判 `^0.2.2-rc.1` 这类范围是否覆盖本机版本（`0.2.2-rc.5` 满足 `^0.2.2-rc.1`）；`<x.y.z-0` 是作者自设的保守上限，**不满足只 WARN 不拦装**。
- **② host inject**：先按 `package.json` 的 `main`/`exports` 定入口（别假设 `lib/index.js`），再 `Select-String -Path <入口文件> -Pattern 'provide\(|ctx\.provide'`；把命中的服务名逐个进 asar 搜——`.mjs` 里 `const b = fs.readFileSync(asarPath); const i = b.indexOf(name); if (i < 0) → 不存在`，命中就截前后窗口读上下文判语义（asar 是单文件明文，`Buffer.indexOf` 是唯一定位手段）。Cordis Inspect（`cordis_inspect_list` / `cordis_inspect_query` 工具，或 GUI 开发者面板）只是精选契约表，**没列出 ≠ 不存在**。

  ```js
  // find-asar.mjs —— node find-asar.mjs "<asar 路径>" "<服务名>"
  import fs from 'node:fs'
  const [asar, needle] = process.argv.slice(2)
  const b = fs.readFileSync(asar), t = Buffer.from(needle)
  const hits = []; let i = b.indexOf(t)
  while (i >= 0 && hits.length < 20) { hits.push(i); i = b.indexOf(t, i + 1) }
  if (!hits.length) { console.log('不存在'); process.exit(0) }
  for (const off of hits.slice(0, 5))
    console.log(off, b.subarray(Math.max(0, off - 150), off + 250)
      .toString('utf8').replace(/[^\x20-\x7e\u4e00-\u9fa5]/g, '.'))
  ```
- **③ client.inject 包存在性**：读 `package.json` 的 `dsh.client.inject` 数组，对每个包名 `Test-Path (Join-Path $profile "node_modules\<包名>")` 或在内核 asar 里搜包名字符串；`optional` 的缺了可以装（只是少功能），非 optional 缺了会白屏。
- **④ 符号级比对**：`.mjs` 里 `const req = createRequire("$deploy/resources/app/package.json")`（路径按实际 app 目录）；把插件源码里 `import { a, b } from '@deepseek-ai/x'` 的符号全 grep 出来，再 `Object.keys(await req('@deepseek-ai/x'))` 逐个比对，缺一个就会 `undefined is not a function`。

  ```js
  // check-exports.mjs —— node check-exports.mjs "<app 目录>/package.json" @deepseek-ai/x a b c
  import { createRequire } from 'node:module'
  const [anchor, pkg, ...symbols] = process.argv.slice(2)
  const req = createRequire(anchor), mod = await req(pkg)
  for (const s of symbols) console.log(s, s in mod ? 'OK' : 'MISSING')
  ```
- **1.1 自建 compat / fork 的 peer 千万别精确钉死**：写范围 `>=0.2.1-rc.2 <0.3.0-0`（覆盖 rc.x、不含 0.3）；改法＝先删 `profiles\desktop\node_modules\<pkg>` 副本，再 `dsh plugin --profile desktop add "<pkg>@file:<绝对路径>"`（pnpm 不刷新 `file:` 副本，见 2.5；`--profile` 别省）；验收＝`dsh plugin --profile desktop list` 无告警，内核每次升级后跑一次。依据见 evidence/ops.md 第 1.1 节
- **1.2 peer 不满足＝只 WARN，不是硬拒**（0.2.2 起）：先装，再看运行时工具能不能调；别因警告就放弃，也别去找 allow-version 豁免。依据见 evidence/ops.md 第 1.2 节
- **1.3 运行时能力也要查**：解包 → 读 inject 与 execute 用到的服务能力 → 在内核 asar 里搜这些能力名 → 再决定；只对版本号会「装得上、第一次调用就崩」。同类：仍按已移除 API（`session.events`；`eventAt/snapshotEvents/ownEvents`）读会话事件的插件活不过第一轮。依据见 evidence/ops.md 第 1.3 节
- **1.4 npm 侧三个陷阱**：①包级——`@deepseek-ai/dsh-tools` 的 `latest` 是旧线 `0.0.1-rc.1`，别写 `^0.0.1-rc.1`；②版本级——更新面板会报 npm 上不存在的版本，装前必须 `npm view <pkg> dist-tags`；③语义级——`latest` 才是正式版，billion-context 还有 `pr`/`master` 上千条，别跟着升。依据见 evidence/ops.md 第 1.4 节
- **1.5 装第三方 UI 插件前「三查」**：①Host 半体 `index.js` 的 `export const inject`（要哪些宿主服务、注册什么路由、Node 版本）②Client 半体 `client.js`（`window.__ModuleLoader__.load` 自注册最抗升级，还是 require 内核包；用了哪些 `ctx.slots.inject` 槽）③扫内核 asar 确认槽名与 API 存在（`indexOf` 槽名字符串即可）。**peer 版本号只说明作者在哪个内核上测过，不等于能跑**；真会炸的是 require 了已删子入口的包。依据见 evidence/ops.md 第 1.5 节
- **1.6 冒烟必须在能解析依赖的目录里做**：把解包目录复制到 `profiles\<profile>\node_modules\<name>-smoketest` 再 import（在 `%TEMP%` 会报 `Cannot find package 'zod'` 这类假 FAIL），验完 `rd /s /q` 并核对无残留；符号级比对用 `createRequire('…/resources/app/package.json')` 动态 import 内核包；取入口按 `package.json` 的 `main`/`exports`，别假设 `lib/index.js`。依据见 evidence/ops.md 第 1.6 节
- **1.7 工具面可达性也是门控项**：判据不是「装完有没有工具」，而是「这套工具能不能到达当前主 agent」——只给值班会话、主 agent 拿不到的等于没装；还要读包里的 `cordis.patch.yml`，README 只说「关闭 6 个插件」却不列名字的，实际会整体替换工作方式。同类需求优先用现成 MCP，别自建抓取。依据见 evidence/ops.md 第 1.7 节

依据见 evidence/ops.md 第 1 节

- **1.8 装一个新的（与升级不是同一件事，2026-11-22 装 `dsh-workspace-explorer` 实测）**：三步——①备份 `package.json` 与 `cordis.patch.yml`；②`dsh plugin --profile desktop add "<pkg>@<ver>"`（registry 包写版本号；未发布的本地包写 `"<pkg>@file:<绝对路径>.tgz"`，`file:` 是长期引用，tgz 归档规矩见 2.5⑧）；③**查 `dsh.profile.bundles` 里有没有它**——`add` 只写 `dependencies`，声明了 `dsh.bundle` 的新包**不会自动进 bundles**（0.2.2 起不 reconcile），没进就 `plugin_manager set_bundle target="<pkg>" enabled=true`，或按 2.2 / 2.3b 动 bundles 数组。**判据**：`dsh plugin list` 有它 **且** `package.json` 的 `dsh.profile.bundles` 有它；只满足前者，重启后工具面里什么都没有。

- **1.9 装完 exit 1 但版本已变＝pnpm 构建审计噪音（2026-11-24 实测，连升 7 个包全部命中）**：输出里同时有 `[ERR_PNPM_IGNORED_BUILDS] Ignored build scripts: onnxruntime-node@1.30.0, protobufjs@7.6.6`、末尾 `Command failed with exit code 1`，但 `- <pkg> 旧` / `+ <pkg> 新` 两行都在。**判据三条全过就算装成功**：`package.json` 的 dependencies spec 是新版、`node_modules/<pkg>/package.json` 的 `version` 是新版、`dsh.profile.bundles` 条数没少且含该包。这两个是 `meow-mind → @huggingface/transformers@4.3.2 → onnxruntime-node@1.30.0` 的传递依赖（2026-11-24 用 `dsh plugin why onnxruntime-node` 核实；此前记成 dsh-video-understand / bili-vision 的依赖是错的，那插件当天已卸、`onnxruntime-node` 287.7 MB 仍留在原地），postinstall 会拉 onnxruntime 预编译二进制（100 MB+），本机用不到也删不掉——记忆插件的 embedding 要它。本机 pnpm 11.28.5 的「放行」开关在 `.npmrc`（被 cc-safety-net 的 `secret.basename.npmrc` 规则拦住，**不能读也不要绕**），在 `pnpm-workspace.yaml` 里加 `ignoredBuiltDependencies` 或 `onlyBuiltDependencies: []` **都不生效**（2026-11-24 已试并回滚，文件恢复到 1566 B 原样）——别反复试，按上面三条判据验收即可。

## 2. 升级流程（六步）

1) `npm view <pkg> dist-tags` 确认真实版本（**更新面板会报出 npm 上不存在的版本**）；拉 tarball 比元数据（体积、文件数、peer/deps 是否一字不变）——多数包**没有 CHANGELOG**，别替作者编，peer/deps 一字不差的多半是纯代码补丁。
2) 备份 `package.json` 与 `cordis.patch.yml`；`dsh plugin --profile desktop add <pkg>@<ver>`（多个包逐条跑）。
3) 核对 **deps / bundles 数量与条目**（判据见 2.1），无掉队无多余。
4) 重启宿主。
5) 验工具面 + 实跑最小用例（哨兵清单见第 8 节）。
6) 在 `C:\deepseek\插件\插件说明.txt` 记一笔（规矩见 5.3）。

- **2.1 第 3 步到底查什么（三条一起看，缺一条就漏）**：deps 条数对不对（**以本轮实测为基**，2026-11-21 是 26，装卸任何插件都会变）；`dsh.profile.bundles` 条数对不对（同口径，2026-11-21 是 38）、目标包在不在；`dsh plugin --profile desktop list` 里目标包在、版本对（**输出是 pnpm 依赖树，没有 `missing bundles` 字段**）、无 `Cannot validate` 告警。**换版必查 bundles**：pnpm 换版会把包从 `dsh.profile.bundles` 删掉（deps 还在、`inBundles=false`），重启后该插件工具全消失或预设加载失败；用 node 按字母序插回原位，复核 declared-bundle 缺失为空。依据见 evidence/ops.md 第 2.1 节
- **2.2 bundles 的 reconcile 分版本两套**：0.2.1 及更早——`dsh plugin` 跑完 pnpm 后按 dependencies 重建，声明 `dsh.bundle` 的依赖自动加回，要持久移除得同时删 dependencies 与 bundles；**0.2.2-rc.1 起不再自动补**，掉出只能在 `profiles\desktop\package.json` 的 `dsh.profile.bundles` 手工加回（原可用 hot-installer 热重载恢复；该插件 2026-11-22 已卸，现在只能重启）；`inspectProfileConsistency` 只报「装了但未声明」，不会自动重加。依据见 evidence/ops.md 第 2.2 节
- **2.3 装完第一次重启是风险点**：症状 `client-modules: duplicate factory registration for "@xxx"`、`Error: web boot: N entry did not activate`，且 `dsh.profile.bundles` 被写回只剩 `dsh-base`+`dsh-web-app`（工具全消失）。处置：备份坏 `package.json` → `dsh plugin --profile desktop remove <坏包>` → 重建 bundles（**有 `bundles-before.txt` 备份就从它恢复**；没有再按「内核 12 条 + deps 里所有声明 `dsh.bundle` 的包」逐条列，别手写整表）→ 校验掉队 0 → 重启看 crash 目录有没有新的 web-boot 日志。**同一版本连崩两次别硬试，换上一个可用版本**。依据见 evidence/ops.md 第 2.3 节
- **2.3b 重建 bundles 时怎么枚举**（别手抄、别手写整表）：存成 `.mjs` 再跑，别用 `node -e`（引号坑）——
```js
import fs from 'node:fs';
const prof = 'C:/Users/ZQY/.dsh/profiles/desktop';
const deps = Object.keys(JSON.parse(fs.readFileSync(prof + '/package.json', 'utf8')).dependencies);
for (const name of deps) {
  try {
    const j = JSON.parse(fs.readFileSync(`${prof}/node_modules/${name}/package.json`, 'utf8'));
    if (j.dsh?.bundle) console.log(name);
  } catch {}
}
```
输出 ＋ 内核自带的 12 条 ＝ 该写进 `dsh.profile.bundles` 的完整列表；写完用 `dsh plugin --profile desktop list` 复核：目标包在、版本对，且 `dsh.profile.bundles` 里没有多出未安装的条目——**这个命令的输出没有 `missing` 字段**（2026-11-21 实测，输出是 pnpm 依赖树），只能人工比对，别去等一个不存在的字段。
- **2.4 升级内核前的取证**：①读 release notes，三类标注——必须手动做的、会打断插件的（API 迁移/协议变更）、只是优化的；②`npm view <pkg> peerDependencies` 核对硬钉（某 UI 插件钉到新版说明内核与它必须成组升）；③grep 本地/自改插件的 API 依赖（`tools.resolve|executable:|agent/request|sessionProjection|tools.mode`），0 命中才敢升；④备份三件到 `work\handover\backups\prof-<日期>\`：`package.json`、`cordis.patch.yml`、`bundles-before.txt`；⑤核对 `node -v` 满足新最低版本（走 `dsh-runtimes` 里的那个 node）。依据见 evidence/ops.md 第 2.4 节
- **2.5 手工动插件目录**（正常升级走 `dsh plugin add`；只有改文件、重放补丁、EPERM、做可移植副本才手工碰）：①**先验源再动目标**——`Test-Path $src` 且断言源 `package.json` 名称版本对得上；②**原子替换，绝不「先清空再拷」**——`Copy-Item $src $dst.new` → 校验文件数与哈希 → `Rename-Item`；源路径写错目标会变 0 文件空壳，**`pnpm install` 修不好**；③**EPERM 绕行**——`ERR_PNPM_EPERM … rename <pkg>_tmp_<pid>` 说明插件 runtime 正被宿主打开，用 node 执行 `fs.renameSync('node_modules/<pkg>','node_modules/<pkg>.broken-<日期>')` 改目录名通常能成，再重跑 add，事后删旧目录（**别用 `node -e`**：pwsh 会吃掉引号，写 `.mjs` 文件再跑，`node --check` 后再执行）。依据见 evidence/ops.md 第 2.5 节
- ④**空壳排查**——`failed to prepare profile bundle` / `cannot resolve profile bundle` 先数 vendor 与 `node_modules` 两侧文件数，0 文件目录删掉再 `pnpm install`；⑤**EPERM 后往往只剩一次机会**——pnpm 失败时已删掉目标 `package.json` 与 `lib`，第二次 add 必须一次成功，`npm_config_package_import_method=copy` 不救，`rm -rf` 会被 CC Safety Net 拦（改用 node `fs.rmSync`）。
- ⑥**别复制 pnpm 管理的 `node_modules`**——符号链接会坏（`Cannot find native binding`）；要可移植副本就用运行时 pnpm 在插件目录 `install --prod --config.node-linker=hoisted`；⑥b **`file:` 包要升级怎么办**：新版 tgz 用 `npm pack <pkg>@<ver>` 现打或从上游 release 下 → 替换原路径的 tgz → 删 `node_modules\<pkg>` 副本 → 再 `dsh plugin --profile desktop add "<pkg>@file:<新路径>"`。只改 `package.json` 的版本号不换 tgz，装回去的还是旧内容。**回滚走同一条路**：把旧版 tgz 换回原路径 → 删 `node_modules\<pkg>` → `add "<pkg>@file:<旧 tgz>"`（按 2.5⑧ 归档过就有旧 tgz，没归档过可能已经拿不到了）。⑦**`file:` 依赖改完 vendor 不刷新**——（这里的 **vendor 指 `profiles\<profile>\node_modules\<pkg>` 那份已装副本**；`profiles\web\vendor` 是另一处，只对内核替换有意义，别混）`pnpm install`（连 `--force`）都不会更新 `profiles\<profile>\node_modules\<pkg>`，正确姿势＝先 `Remove-Item profiles\<profile>\node_modules\<pkg> -Recurse -Force` 再 `pnpm install`，最后核对 version 与特征代码。
- ⑧**`file:` 指向的 tgz 是长期引用**——删了 tgz 会让**下次任何 `dsh plugin`（pnpm install）失败**；装完立刻归档到 `C:\deepseek\tools\archives\`，再用 node 改依赖字符串、`dsh plugin list` 验证无告警；⑨**改代码必须同时升版本号**（新能力跳小版本、纯修 bug 跳补丁位）并在 README 记一节，否则回滚与分发时认不出这批改动。
- **2.6 卸载六步**：①备份 `package.json` 到 `handover\backups\`；②`dsh plugin --profile desktop remove <包名>`；③核对 deps 与 bundles 条数都变了、目标包两边都消失、`dsh.profile.bundles` 里没有残留条目（同样没有 `missing` 字段可看，人工比对）、原生工具（如 `pwsh`）当场恢复；④查残留四处——`cordis.patch.yml` 配置块、`.credentials.yaml` 凭据、`~\.dsh\<插件名>\` 与 `storages\<插件名>\` 数据目录、它收发的媒体文件；⑤扫技能引用——包名与工具名前缀 grep `~/.agents/skills` 与插件自带 `SKILL.md`，命中处加「YYYY-MM-DD 起已卸」标注**而不是删段**；⑥同步 `C:\deepseek\插件\插件说明.txt` 与记忆。
- **清理边界**：可清——更新器 `pending\`（已装版本的重复下载）、`harness\cache`（compile-cache / request-images 可重建）、`%TEMP%\dsh-*`（以 `[desktop] starting` 那行为界，早于 boot 可删、晚于 boot 属当前会话）、空壳会话目录（0 B～1 KB）、工作区里自写的排查脚本与 `.bak`、插件 venv 的 `__pycache__`；**勿删**——`%TEMP%\dsh-acl-locks`（运行时锁）、仍在被引用的备用引擎 venv。注意 nvidia 那套：2026-11-24 起 `dsh-video-understand` 已卸、它的 `.venv`（含 cuBLAS/cuDNN 约 2 GB）也一并消失；现在 GPU ASR 挂在 `~\.dsh\bili-vision-venv`，要恢复 GPU 得自己 `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`，别去别处找那套包。
- **删前先 grep 默认路径**：目录名带 test 也可能是生产默认值（`tools\mineru4-venv` 是 MinerU 4.x 通道解释器、`tools\sci-venv` 是科研链默认 python）——全库与配置默认值 0 命中、且 handover 证据没引用，才可删。`tools\mineru3-test\venv`（6.6 GB）自 2026-11-25 起已不被代码引用（插件与技能都改指 `mineru4-venv`），但它是 3.x 的回退路径，删之前先确认 4.x 跑顺了、`pip freeze` 备份还在（`handover\mineru-3.4.5-freeze.txt`）。
- **删会话目录会让宿主重启**：用 node `fs.rmSync` 删 3 条测试会话目录后约 10 秒 DSH 全部进程重启、hot-installer 重新打 active（该插件 2026-11-22 已卸，此处为当次实测记录）；判据＝删完 10 秒内断线重连先怀疑删除动作，做法＝会话运行中不删，先停宿主。
- **别误删清单**：`C:\deepseek\官方`（程序本体）、`~\.dsh`（profiles/sessions/storages/凭据）、`C:\deepseek\插件`（archives/patches/forks + raw-html clone 活引用）、`C:\deepseek\tools`（bili-mcp cookie、bin 的 ffmpeg、sci-venv、mineru4-venv、archives、dsh-doc-parser）、`C:\deepseek\work\handover`、`~\.agents\skills`。盘占用逐包递归求和再报；僵尸依赖（声明了没装）不占空间、不能算收益，功能刚需的 venv 删了是阉割不是瘦身。依据见 evidence/ops.md 第 2.6 节

- **2.7 装失败时的三类 pnpm 错误（2026-11-21 实测补）**：
  - `ERR_PNPM_IGNORED_BUILDS`——pnpm 10+ 默认不跑依赖的构建脚本。放行：`dsh plugin --profile desktop add "<pkg>@<ver>" --config.strict-dep-builds=false`（`--config.*` 会被转发给 pnpm）。**判据**：先读错误点名的包名，只有该包确实要跑 postinstall（原生模块、二进制下载）才放行，纯 JS 包不必。
  - `ERR_PNPM_EPERM … rename <pkg>_tmp_<pid>`——见 2.5④；失败后先看 deps 是否已写半截、`node_modules` 有没有空目录。
  - 回滚一行：`dsh plugin --profile desktop add "<pkg>@<上一版>"`（`file:` 包见 2.5⑥b）。

## 3. 工具突然消失（三步排查）

1. **看清单**：`profiles\desktop\package.json` 的 `dependencies` 与 `dsh.profile.bundles`——**0.2.2 起 bundles 掉出不会自动补**，单包掉出时手工加回即可。
2. **看文件**：`node_modules\<pkg>` 是否 symlink、指向的源码在不在、`node --check` 过不过。
3. **看告警**：`dsh plugin --profile desktop list` 的 warning。最常见 `Cannot validate installed package … SyntaxError: Unexpected token '﻿'`——package.json 被写成 UTF-8 带 BOM（PowerShell `Set-Content -Encoding UTF8` 造成），用 node 剥掉 BOM 即好。改完 bundles **必须电源键完全退出重启**：原 hot-installer 能热重载装配表，但它从不重新注册工具，而该插件 2026-11-22 已卸，现在没有任何热路径。
4. **旧结论 → 现结论**：单包掉出可手工加回 `dsh.profile.bundles`（只动这个数组是安全的）；若整表被写回只剩 `dsh-base`+`dsh-web-app` 两条，`dsh plugin add <已装包>` 修不回来，只能去界面插件管理页逐个启用，或用 `plugin_manager set_bundle`（**别整表手写、别改 `dependencies`**，那是另一个坑）。依据见 evidence/ops.md 第 3 节
- **3.1 重启后验活四步**：①从 `harness.log` 的 `[stdout] dsh web: http://127.0.0.1:<port>/?token=...` 取端口与 token（取前核对端口属于活着的主进程）②直探插件路由——**200**＝在、**405**＝路由已注册但方法不对、**404**＝不存在 ③取启动页两步：先 `GET /?token=<tok>` 拿 303 + `Set-Cookie dsh-auth-*`，**带 cookie 再取 `/`** 才 200（直接带 token 会 401，报 `dsh web authentication required; reopen the URL printed by dsh web`）④HTML 里的 `/plugins/??a/client.js,b/client.js&rev=…` 是本次注入清单；直 GET `/plugins/<pkg>/client.js` 必 404，要带 `&rev`。**时机陷阱**：boot 段干净 + 隔 1–2 分钟同一脚本重跑一致＝时机问题，不是插件坏了，别急着回滚。**热重载**：`applied` 只表示配置已应用，不代表工具挂载就绪；要重载就等几秒，先用无关工具探活。依据见 evidence/ops.md 第 3.1 节
- **3.1b 端口别信日志最后一条**：`[stdout] dsh web:` 行会被自己跑的冷启动探针污染（探针被杀、URL 还留在日志）；按 PID 核端口归属——`Get-NetTCPConnection -LocalPort <port> | Select-Object OwningProcess`，或直接用宿主给的 GUI 地址。
- **3.2 启动就失败三种形态**：`desktop welcome: Web authentication failed`→HTTP 431 Cookie 头超限（`--port 0` 随机端口 + `dsh-auth-*` cookie 30 天不清），修法 `dsh-auth-cookie-sweep` 治本 / `dsh-cookie-guard` 30→7 治标，完全打不开先退出 DSH（含托盘）再删 `%APPDATA%\@deepseek-ai\dsh-desktop\Network\Cookies`；实体目录代替 junction→把 `$DSH_HOME\profiles\node_modules\@deepseek-ai\` 下真实目录移走备份，下次启动自动重建；`Error: web boot: N entry did not activate`→见 2.3。依据见 evidence/ops.md 第 3.2 节
- **3.3 装配表里的 id ≠ 包名**：拿包名当子串 grep `--dump-config` 会误判缺失（`billion-context-dsh` 的 id 是 `compaction-acp`，`modsearch` 的 id 无 scope）；列全部 `^\s*- id:\s*(\S+)` 行再对照，或按「包名 + 已知别名」一起找。依据见 evidence/ops.md 第 3.3 节
- **3.4 预设面板报「加载失败」**：几乎总是某一行插件导入或 schema 校验炸；解 app.asar 读 `const Config = z.object(...)`，看 `record.broken` 与 `auditRows` 里的 never started / await 抛错 / 缺注入服务。修法：删该行、改 `modelSelection:true` + `modelDiscovery:true`、删 `backgroundMode`；这个预设补丁每次升级都要重放（第 6 节）。依据见 evidence/ops.md 第 3.4 节

## 4. 内核更新失败

- **4.1 形态与善后**：`desktop update: Host did not complete graceful task teardown (exit null, signal SIGTERM, shutdown acknowledged true, graceful deadline exceeded true)`——更新器等宿主优雅收尾超时强杀，**版本原地不动**。先查 `%LOCALAPPDATA%\@deepseek-aidsh-desktop-updater\pending\` 的安装包下完没有（**目录名把 scope 与包名连在一起，中间没有反斜杠**）（有 `.exe` + `update-info.json` 就是下完了），**完全退出（电源键，不是关窗口）再重开**会自动装，没装再点一次更新。
- 最坑后果：bundles 被写成 2 条，插件都在 `node_modules` 却全没挂上、工具面全丢（处置见 3 节末）。缓解：更新前退出后台任务、挑空载时机；更新器里 `installer.exe` + `current.blockmap` 是差分更新基线，别当垃圾删。
- **4.2 升级前必读**：0.2.2-rc.1 的破坏项清单——最低 Node 24.9；Cordis Core 4.1.0 / Loader 1.1.0 / Include 1.1.0；插件迁 `tools.resolve`/`executable` 与提示词组装接口；PTC 拆成按 Agent 作用域的插件（`tools.mode` 迁移、控制通道 birpc、SSH 2→3）；Session Projection 注册改异步；`agent/request` 改走 `agent.model`；官方组合包改由 `@deepseek-ai/dsh-official-bundles` 导出；文件修改先读防护与 apply_patch 默认关闭。**必须手动做的一条**：升级前把 `@deepseek-ai/dsh-experimental-tool-worktree` 从 `dsh.profile.bundles` 与 `dependencies` 里都删掉。依据见 evidence/ops.md 第 4.2 节
- **成组升级**：内核与 `dsh-better-sidebar 0.30.x`（peer 钉 `^0.2.2-rc.1`）、`dsh-context 0.81.x` 必须一起升。Session 事件 API 链：0.1.2-rc.1 移除 `session.events` → 0.1.7-rc.2 弃用 `eventAt/snapshotEvents/ownEvents`、`agent/session-start` 换 `agent/created`——按老 API 读会话事件的插件都会失效。
- **4.3 禁用一个内核能力前，先把 inject 映射到提供者**：改 `disabled` 列表时逐个把 inject 项映射到提供者，确认链条每一环都恢复；只放行命令不恢复服务等于没修（如 `command-compact` 的 `compaction` 服务由 `compaction-basic` 提供）。依据见 evidence/ops.md 第 4.3 节

## 5. 版本判定（三处取数，别只看一处）

- **内核**：`dsh.cmd --version` 与 exe FileVersion **双证**（桌面前台时 `--dump-config` 会报错，`--version` 可用）；路径 `C:\deepseek\官方\resources\runtime\cli\bin\dsh.cmd`。
- **插件**：用 **node** 读 `node_modules\<pkg>\package.json`——PowerShell `ConvertFrom-Json` 读 UTF-8 中文会抛「传入的数组无效」并静默沿用上一个对象；临时代码写 `.mjs` 再跑，避开 `node -e` 引号坑。
- **registry**：`npm view <pkg> dist-tags`（`latest` 正式版、`next` 预发布；例外见 1.4）。
- **5.1 内核与外壳说明分两条线**：内核 `https://github.com/deepseek-ai/deepseek-harness/releases.atom`（公开仓库，每条 `<content type="html">` 就是 release 正文，按 `(?s)<entry>(?:(?!</entry>).)*?</entry>` 分条，atom 不占 API 60/h 配额）；**仓库全名从 `package.json` 的 `repository` 取，别用简称猜**；内核安装包独立于外壳：`%LOCALAPPDATA%\@deepseek-aidsh-desktop-updater\pending\deepseek-harness-<ver>-win-x64.exe`（exe 版本资源即内核版本）。外壳 `https://dshdesktop.com/updates/latest/latest.yml`（真实 feed 见 `C:\deepseek\官方\resources\app-update.yml`：`https://download.deepseek.com/dsh-desk/feeds/win-x64/`），字段 `version`（**外壳**版本，不是内核）、`releaseDate`、`releaseNotes`；GitHub 侧是 `dataelement/dsh-desktop` releases。
- 坑一：`Invoke-WebRequest` 取 yml 返回 **byte[]**，要 `[Text.Encoding]::UTF8.GetString()`。坑二：`releaseNotes` 可能滞后于实际内核——两条线分别取证，别拿说明当版本号。依据见 evidence/ops.md 第 5.1 节
- **5.2 pending 里有安装包 ≠ 有新版本**：①取渠道清单读 `version`/`size`/`sha512`（node fetch 可用，IWR 不通）②对 `%LOCALAPPDATA%\@deepseek-aidsh-desktop-updater\pending\deepseek-harness-<ver>-win-x64.exe` 算 sha512(base64)（**外壳设置包与内核包不同名**，别拿错）（`node:crypto`）③一致＝同版本重复下载，重启安装不会有任何变化，可直接清 pending。判断「要不要升级」要对两侧取证：已装版本（exe VersionInfo + `resources\app\package.json`）与渠道声明。依据见 evidence/ops.md 第 5.2 节
- **5.3 更新说明取不到时怎么写**：上游正文中文被写坏（整段 `????`）→ 保留可读部分（标题、英文术语、代码块）+ 用本地 tarball 实测复原，交付里**明确标注「非原文照抄」**；仓库未发 release → 以 npm dist-tags + 包内 README 的 Changelog 为准，写明「仓库无 release」；完全取不到 → 明写「上游未提供说明」并给可比对事实（解包体积、文件数、入口字节数、行为差异），不能只报版本号。
- **上游 404 先分两种**：换出口/代理就通＝网络问题，退避重试一次；所有出口都 404＝真下线/改名/转私有，写「上游 404，无法核验」，本地留 tgz + `SHA256SUMS` 才有回滚路径，别写成「已是最新」。
- `C:\deepseek\插件\插件说明.txt` 是本地权威表：每个版本号都要能从 profile 或 `node_modules\<pkg>\package.json` 核到；改版本号**不要全局替换**，只改实装表那几行，改完 grep 历史区核对。依据见 evidence/ops.md 第 5.3 节

## 6. 带本地补丁的包怎么升

1. **先查作者修没修**：解新 tarball，对比本地改了的那几行；`dsh.bundle.patch` 列的文件会被新版整体覆盖，所以要逐字节比 + grep 修补标记——一致＝必须重放，不一致＝作者已修、补丁标 stale。取包：`https://registry.npmjs.org/<name>/-/<name>-<ver>.tgz` → `tar -xzf`（Windows 自带 bsdtar）。
2. 已修 → 补丁作废，重放前先判断还需不需要；未修 → 按新版本重做补丁，命名 `<pkg>-<新ver>-<要点>.patch`。
3. **升级后补丁必然消失**（npm 装出来就是上游原版），别按惯性先跑「原始 tarball vs 实装」diff——两边字节相同，白跑一轮。
- **重放五步**：①把改动重新施加到新文件——按行定位 `^function <name>(` 与其后第一个 `^}` 整块替换，**绝不要用 `[\s\S]*?\n  \}` 这类跨函数正则**（`replace()` 不报错、坏文件当场写盘）；②**写盘后立刻断言**——其他函数名仍在 + 字符增量 == 新块长 − 旧块长；③`git diff --no-index --no-prefix --output=…`（容忍退出码 1）；④**双向验证**——正向 SHA256 相等 + `git apply -R --check` 通过 + 抽函数跑单测；⑤落 `patches\`、删旧补丁；任一步不过就从原始 tarball 回滚重来。依据见 evidence/ops.md 第 6 节
- **三个边界坑**：`--no-prefix` 正反两侧必须**同层同名**（造 `a/lib/index.js` / `b/lib/index.js` 配对目录再 diff，否则 `-p1` 报 `git diff header lacks filename information`）；函数收尾锚风格随版本变，取较近者 `Math.min(indexOf("\n}")+2, indexOf("\n  }")+4)`；`core.autocrlf` 会把 LF 写 CRLF 导致 `Buffer.equals` 假报不一致，比对前统一 `.replace(/\r\n/g,"\n")`。依据见 evidence/ops.md 第 6 节
- **补丁是否真落地，用 mtime + 内容双验**：改插件内部文件（如 `presets/*.patch.yml`）必须确认改的就是宿主真正加载的那份 `profiles\desktop\node_modules\<pkg>\...`——命令退出码不算证据。依据见 evidence/ops.md 第 6 节
- **在册要重放的补丁**（每次升级按此表重放）：`patches\_obsolete\reapply-market-entry-off.ps1`（2026-11-19 已移入 `_obsolete\`，需要时取回重打）——桌面升级会整体重写 `resources\`，抹掉插件市场入口的 `disabled: true`，脚本幂等、保 CRLF、`-CleanPending` 清同版冗余安装包；能落在 harness home（`profiles\web\vendor`、`cordis.patch.yml`、`settings.yaml`）的改动优先落那边，不受应用升级影响。
- `skills\dsh\scripts\studyhub-preset-patch.mjs`（`C:\deepseek\tools\` 下曾放同名副本，2026-11-24 起以技能里这份为现行版）——StudyHub 自带 `presets/study.patch.yml` 长期不改（`tool-subagent-list-agents`、`modelSelectionSettings: true`、两处 `backgroundMode: continuable`），每次升级重放；幂等、`--check` 只报告、目标固定为宿主加载那份。**校验依赖**：用 `js-yaml` 解析改后的 YAML，该包**随脚本放在同目录 `scripts\node_modules\js-yaml`**（先 `createRequire(import.meta.url)` 再 `require("js-yaml")`）——本机没有全局 node/npm，profile 也没装 js-yaml，之前 `createRequire(PROFILE/package.json)` 会报 `Cannot find module 'js-yaml'`。**触发时机不止升级**：该文件会被别的原因写坏，判据＝看文件 mtime 与内容里有没有旧写法，别等升级才发现。**触发时机不止升级**：该文件会被别的原因写坏，判据＝看文件 mtime 与内容里有没有旧写法，别等升级才发现。`skills\dsh\scripts\billion-ungate-patch.cjs`——billion 的 `dist/agent/dsh-compaction-gate.js` 在 `internal/config` 钩子里把 `dsh-compaction-basic`/`dsh-command-compact` 设 `disabled:true`（`/compact` 消失），补丁改掉该判断，billion 升级会覆盖要重跑；该命令一直挂在 dsh-base patch 上，从来不是内核移除。
- 皮肤类 `patches\replay-skins-deblur.py` 升皮肤后必须重跑；附件类补丁（如 raw-html 的「首次捕获自动重挂载一次」）每次升级按上节流程重放，并用 `node --check` 过一遍。依据见 evidence/ops.md 第 6 节

## 7. Windows 侧坑（高频）

- 写 JSON／配置**用 node 写**；PowerShell `Set-Content -Encoding UTF8` 会带 BOM，导致插件静默失效（`Cannot validate installed package … Unexpected token '﻿'`）。给用户双击的 `.bat` 一律**纯 ASCII**（中文 + `chcp 65001` 救不了，cmd 按系统 ANSI/GBK 解析文件本身）。
- `node` 不在 PATH：`C:\Users\ZQY\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe`，pnpm 用同目录 `pnpm\bin\pnpm.cjs`。调 Python 别用 `-c` 内联复杂代码，写临时 `.py` 再跑；PATH 里的 `python` 是商店假 stub，`pythonPath` 显式指真路径或自建 venv。
- **winget 装的 PowerShell 是 Store 版**：落 WindowsApps 别名、没有 `Program Files\PowerShell\7`，要占第一优先路径必须装 MSI；装完实测 `ProcessPath` 与编码/BOM，别按包名假设路径。
- **`edit` 的前置条件**：目标文件在「上次 read 之后被修改过」（哪怕自己改的）再次 edit 会被拒，报 `file has not been modified? cannot modify ...: file has not been read — read the file, then retry`；批量改长文档要么一次读完一口气提交，要么每次改前重读。
- `workdir` 指向不存在的目录报 `spawn ...powershell.exe ENOENT`（像 shell 丢了）且一条命令都不执行——先 `Test-Path` 再建目录。pwsh 一启动就报 `grantWrite(工作区) failed`＝工作区权限缺项，用 `diagnose-windows-sandbox-acl` 对工作区自身跑一次（需提权一次）。
- **共享准则文件被拒不是 ACL**：`~\.dsh\AGENTS.md`、`C:\deepseek\共享\agent-准则.md` 在 workspace-write 下必被拒，带 `danger-full-access` 重试一次即可；先跑 ACL 修复是白跑（报错是 `sandbox: file access denied`）。
- **代理两条链路不能混**：node 的 `fetch` 不读 Windows 系统代理（`HTTP_PROXY` 对 undici 也不生效），抓被墙地址用 `Invoke-WebRequest -UseBasicParsing`，抓 npm registry 用 node fetch；关掉代理后访问 github 是 **DNS 解析失败**而非超时，可用来区分「代理没开」与「网络断了」。
- **移动插件目录前查活引用**：`node_modules\dsh-raw-html-v2` 是 junction 指向 `C:\deepseek\插件\dsh-raw-html-v2`（`Get-Item -Force | Select LinkType,Target`），移动 clone 会断链。裁剪长文档别直接删旧内容：先把原文整份复制成历史存档冻结，再重写精简当前版。
- **清理临时目录前先看里面有没有工具脚本**（曾有把视频缓存目录连同 bili-mcp 调用器一起清掉的教训）；缓存放子目录、工具统一收进 `C:\deepseek\tools\`，清理按子目录删。
- **技能与插件的发现规则**：用户级 `$DSH_HOME\skills` 与 `~\.agents\skills`；项目级 `<projectRoot>\.dsh\skills`、`<projectRoot>\.agents\skills`（projectRoot＝最近含 `.git` 的祖先，没有则 cwd）。只扫**一层** `<root>\<name>\SKILL.md` 或 `<root>\<name>.md`；frontmatter 必填 `name`/`description`；目录由 chokidar 监听，新建/改名/删除即时刷新。依据见 evidence/ops.md 第 7 节

## 7.5 三个「看起来正常」的假象

- **功能缺失先查是不是「已装但被禁用」**：profile 配置里 `enabled: false` 会让人以为这个能力不存在（典型是 `/compact` 这类内置命令）。先看 `dsh.profile.bundles` 与本地插件配置的 `enabled` 字段，再去看实现代码。
- **皮肤会盖住不走标准 slot 的面板**：`backdrop-filter` 加高 `z-index` 的皮肤层能盖住 `[class*=centerCol]` 之类的面板，症状是「面板在但看不见」。改皮肤时先关掉皮肤验一次。
- **编队数字是父会话的历史投影，不是磁盘残留**：`list_agents` 与面板上的 agent 计数按父会话记录推，删了文件也不会立刻减。要判真实存活看各 agent 的 `status` 与进程，不看数字。

## 8. 验收哨兵（每次升完都要过）

- 工具面里该出现的工具真的在（不是只查列表）；**实跑一次最小用例**（读一页、查一次、导出一次），而不是「列表里有就算成功」。关键路由 200/401 正常、GUI 端口在监听；客户端半改完先 `Ctrl+Shift+R` 再判断。记忆类插件：`memory_search` 能召回一条旧事实。
- **插件更新有没有生效：先比两个时间**，别急着重启——`Get-Process` 里 DSH 的 `StartTime` 晚于源码文件 mtime，新代码就已在内存里（本次 21:52 启动 vs 16:16 定稿，实测新功能全在）。再分两层验：黑盒看工具行为（新参数被接受吗、输出文案变了吗），白盒读缓存 JSON 看字段（schema / withImages / 文件路径 / blocks.type）。**只读 README 不算验收**——文档可能写的是「已修」，要落在磁盘和输出上。
- **退出码不是判据**：一次性 headless 探针里记忆类插件（meow-memory 已卸、现为 meow-mind，同一套调度代码）会让进程回合完成后永不退出（dream 调度/心跳定时器未 unref），属既有特性；判据取「stdout 是否出现预期答复 + 会话日志有无 turnError」，姿势＝`Start-Process` 重定向 stdout + 自行轮询超时再杀。依据见 evidence/ops.md 第 8 节
- **隔离探针**：`profiles\probe` 的 `package.json` 里 `dsh.profile.bundles=[dsh-base, dsh-headless, 被测插件]`，依赖写 `file:../web/vendor/<pkg>`，`pnpm-workspace.yaml` 照抄 web，`cordis.yml=[]`；`pnpm install` 后 `node bin.js --profile probe "<task>"`，验完 `rd /s /q` 删除，JSON 必须无 BOM。**副作用**：探针会话按 cwd 落进 `sessions\<workspace-slug>\`（不按 profile）→ 混进主侧栏，删 probe profile ≠ 删会话；根治＝给独立工作目录（`Start-Process -WorkingDirectory`）。
- **别拿 univer_new 建探针文件**（用户明确否掉）：每建一次 `.univer` 侧栏就多「文档」面板、每轮刷新恢复视图，Univer 锁死文件删不掉；替代＝只查工具面 `univer_*` 在不在 + `dsh-univer-office` 在 bundles 里，非要验读写用 `univer_status` 读已存在文件。
- **压缩类插件的最小闭环**：隔离 profile（base+headless+插件）+ `DEEPSEEK_API_KEY`；`dsh <profile> --json -` 从 stdin 喂任务、`--session-id <id>` 续会话；先塞约 10K token 长材料、再空转 6 轮把目标滚出 protected zone（最后 5 条消息 + 最新用户消息不可压）；看到 `Compressed N block(s), ~X tokens reclaimed`；新进程 resume 后 `acp_status` 仍显示 block active、`search_context` 能命中原文，才算闭环通过。
- **报告格式**：三方插件清单必须是表格——**一个插件一行、五列（插件 / 版本 / 来源 registry·link·file / 状态 正常·异常·已卸 / 一句话用途）、不分组**（与 selfcheck 第 3 节同口径）。
- **对账（四件）**：①记忆体检——`>800` 字先压、按四类判断（错误 / 重复 / 已完结 / 超长）当场修完；②技能引用——grep 旧包名、旧工具名、已卸插件名（真正会过期的是脚本与 cross-reference，不是 md 正文），命中处加「YYYY-MM-DD 起已卸」标注而非删段；③`插件说明.txt`——每个版本号都要能从 `package.json` 核到；④脚本与流程图——本轮行为变化是否要改脚本或文档。三条底线：每个技能都写「名字 + 一句话用途 + 触发场景」（只报总数不合格）、记忆体检当场修完、不许新旧两套描述并存。
- **升级记录**：每次附「这次改了什么」；取不到说明就明写并给可比对事实。装完先把 deps/bundles 核对完再收工（数量以本轮 `dsh plugin --profile desktop list` 实测为准，`SKILL.md` 第 4 节只是量级参考）。

**三个常被含糊使用的词，定义如下**（验收时按这个判，别各理解各的）：
- **重启宿主**：GUI 右上角电源键「完全退出」再重开——不是关窗口、不是刷新页面。命令行启动的实例，杀进程树后重开同一命令。
- **工具面**：当前主 agent 能看到的工具清单（不是 GUI 的插件列表）。判据＝在本会话里工具名能被调用并返回结果；只出现在列表里、主 agent 调不到，算没装上。
- **最小用例**：对该插件**最能暴露「装上了但没生效」的一次真实调用**——文件类读一页/导一次，检索类查一条已知关键词，MCP 类调一次只读接口，记忆类 `memory_search` 召回一条旧事实。判据是返回内容正确，不是「没报错」。
