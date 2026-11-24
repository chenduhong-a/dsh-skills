// 让 billion-context 不再禁用内核压缩（恢复 /compact）
// 用法：node billion-ungate-patch.cjs [--check]
// 背景：billion-context 的 dist/agent/dsh-compaction-gate.js 在接管压缩时，
// 会把 @deepseek-ai/dsh-compaction-basic 与 @deepseek-ai/dsh-command-compact
// 两行设成 disabled:true，导致 /compact 从命令面板消失。本补丁把该判断改成 if(false)。
const fs = require('node:fs');
const path = require('node:path');

const target = 'C:/Users/ZQY/.dsh/profiles/desktop/node_modules/billion-context/dist/agent/dsh-compaction-gate.js';
const from = 'if(r.name===DSH_COMPACTION_BASIC_PACKAGE||r.name===DSH_COMMAND_COMPACT_PACKAGE){return{...r,disabled:true}}';
const to = 'if(false){return{...r,disabled:true}}';
const checkOnly = process.argv.includes('--check');

if (!fs.existsSync(target)) {
  console.log('SKIP: gate file not found (billion-context 可能没装或版本变了)');
  process.exit(0);
}
const src = fs.readFileSync(target, 'utf8');

if (src.includes(to) && !src.includes(from)) {
  console.log('OK: 已经是启用内核压缩的状态，无需重打');
  process.exit(0);
}
if (!src.includes(from)) {
  console.log('WARN: 没找到预期的那段判断 —— billion-context 可能改了实现，需人工看一下：');
  console.log('      ' + target);
  process.exit(1);
}
if (checkOnly) {
  console.log('NEED PATCH: gate 仍在禁用内核压缩，运行不带 --check 即可修补');
  process.exit(0);
}
const bak = path.join('C:/deepseek/插件/backups', 'dsh-compaction-gate.js.' + new Date().toISOString().slice(0, 10).replace(/-/g, '') + '.bak');
if (!fs.existsSync(bak)) fs.writeFileSync(bak, src, 'utf8');
fs.writeFileSync(target, src.split(from).join(to), 'utf8');
console.log('PATCHED: ' + target + '  (backup: ' + bak + ')');
console.log('重启宿主后 /compact 应重新出现在命令面板');
