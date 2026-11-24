#!/usr/bin/env node
/**
 * studyhub-preset-patch.mjs — 把 StudyHub 自带的 study 预设修到能挂在 DSH 0.2.2 上。
 *
 * 背景：StudyHub 的 tgz 里 `presets/study.patch.yml` 一直是 0.2.0 时代的写法，
 * 每次升级重装都会把它覆盖回旧模板，导致「学习模式 · StudyHub」显示加载失败：
 *   1. `@deepseek-ai/dsh-tool-subagent-control/list-agents` 这个子入口在 0.2.2 已不存在；
 *   2. `dsh-tool-subagent` 改用 schemastery `.strict()`，旧键 `modelSelectionSettings`
 *      被拒（新键是 `modelSelection` + `modelDiscovery`）；
 *   3. 旧的 `backgroundMode: continuable` 同样不再被接受。
 *
 * 用法：装完/升级完 StudyHub 之后跑一次；幂等，改过了就只报告。
 *   node C:\Users\ZQY\.agents\skills\dsh\scripts\studyhub-preset-patch.mjs
 *   node C:\Users\ZQY\.agents\skills\dsh\scripts\studyhub-preset-patch.mjs --check   # 只检查不写
 * 依赖：校验用 js-yaml，已随脚本放在同目录 node_modules\js-yaml（不依赖 profile 装了什么）。
 */

import fs from "node:fs";
import { createRequire } from "node:module";

const PROFILE = "C:/Users/ZQY/.dsh/profiles/desktop";
const FILE = `${PROFILE}/node_modules/@ericwang1358/dsh-daily-flashcard/presets/study.patch.yml`;
const checkOnly = process.argv.includes("--check");

if (!fs.existsSync(FILE)) {
  console.error(`[study-preset] 找不到预设文件：${FILE}`);
  console.error("[study-preset] 先确认 StudyHub 已装在 desktop profile。");
  process.exit(1);
}

const original = fs.readFileSync(FILE, "utf8");
let text = original;
const changes = [];

// 1) 删除已经不存在的 list-agents 行（两行）
const before1 = text.length;
text = text.replace(
  /^[ \t]*- id: tool-subagent-list-agents\r?\n[ \t]*name: '[^'\r\n]*\/list-agents'\r?\n/m,
  "",
);
if (text.length !== before1) changes.push("removed tool-subagent-list-agents row");

// 2) modelSelectionSettings（及其后的注释与 backgroundMode）换成新键
const before2 = text.length;
text = text.replace(
  /(\r?\n)([ \t]*)modelSelectionSettings: true[ \t]*\r?\n(?:[ \t]*#[^\r\n]*\r?\n)*[ \t]*backgroundMode: continuable[ \t]*\r?\n/g,
  (_m, nl, indent) => `${nl}${indent}modelSelection: true${nl}${indent}modelDiscovery: true${nl}`,
);
if (text.length !== before2) changes.push("modelSelectionSettings -> modelSelection + modelDiscovery");

// 3) 删除残留的旧注释与 backgroundMode（fork 那一处）
const before3 = text.length;
text = text.replace(/(?:[ \t]*#[^\r\n]*\r?\n)?[ \t]*backgroundMode: continuable[ \t]*\r?\n/g, "");
if (text.length !== before3) changes.push("removed leftover backgroundMode");

// 4) 头部说明里若还写着旧行为，补一句维护提示（只在确实改过时加）
const NOTE = "# 维护：StudyHub 每次升级重装都会覆盖本文件，装完请跑\n#   node C:\\Users\\ZQY\\.agents\\skills\\dsh\\scripts\\studyhub-preset-patch.mjs\n";
if (changes.length > 0 && !text.includes("studyhub-preset-patch.mjs")) {
  text = text.replace(/^(#.*\r?\n)+/, (head) => head + NOTE);
}

// 校验：替换掉 !!js 表达式后用 js-yaml 解析（js-yaml 随脚本放在同目录 node_modules）
function validate(source) {
  const require = createRequire(import.meta.url);
  const yaml = require("js-yaml");
  const safe = source.replace(/!!js\s+.*$/gm, "js-expr");
  const doc = yaml.load(safe);
  const preset = doc?.[0]?.insert?.[0];
  if (!preset || preset.config?.id !== "study") throw new Error("解析后找不到 study 预设声明");
  const rows = preset.config.plugins || [];
  const delegation = rows.find((row) => row.id === "delegation");
  if (!delegation) throw new Error("delegation 组缺失");
  const ids = delegation.config.map((row) => row.id);
  if (ids.includes("tool-subagent-list-agents")) throw new Error("list-agents 行仍在");
  const subagent = delegation.config.find((row) => row.id === "tool-subagent");
  const keys = Object.keys(subagent?.config || {});
  const bad = ["modelSelectionSettings", "backgroundMode"].filter((k) => keys.includes(k));
  if (bad.length) throw new Error(`tool-subagent 仍有旧键：${bad.join(", ")}`);
  return { plugins: rows.length, delegation: ids };
}

let report;
try {
  report = validate(text);
} catch (error) {
  console.error(`[study-preset] 校验失败：${error.message}`);
  console.error("[study-preset] 没有写回文件，原文件保持不变。");
  process.exit(2);
}

if (changes.length === 0) {
  console.log("[study-preset] 无需修改，文件已是 0.2.2 兼容写法。");
} else if (checkOnly) {
  console.log(`[study-preset] --check：需要修改 ${changes.length} 处：${changes.join("; ")}`);
} else {
  fs.writeFileSync(FILE, text, "utf8");
  const stat = fs.statSync(FILE);
  console.log(`[study-preset] 已修补 ${changes.length} 处：${changes.join("; ")}`);
  console.log(`[study-preset] 文件 ${stat.size} B，mtime ${stat.mtime.toISOString()}`);
  console.log("[study-preset] 预设是启动时挂载的，重启宿主后生效。");
}

console.log(`[study-preset] 解析通过：${report.plugins} 个 plugins；delegation = ${report.delegation.join(", ")}`);
