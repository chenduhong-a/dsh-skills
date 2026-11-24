#!/usr/bin/env node
// selfcheck.mjs — DSH 完整自检（快检 / 全检）
//
// 用法：
//   node selfcheck.mjs --quick    快检：内核 / 依赖 / 插件版本 / 记忆哨兵 / 服务端口（约 5~10 秒）
//   node selfcheck.mjs --full     全检：十二项（扫 .dsh 约 20~40 秒）
//   node selfcheck.mjs --diff     只打印与上一次的差分
//   node selfcheck.mjs --only 06,08   只跑指定项（项号见下），不落档、不做差分
//         01 内核 / 02 依赖 / 03 插件版本 / 04 插件目录 / 05 B站MCP / 06 技能
//         07 记忆 / 08 工作区 / 09 HOME / 10 外部通道 / 11 更新检查 / 12 使用统计
//         例：只查自建技能与当前工作区 → --only 06,08
//
// 产物：
//   stdout  人类可读摘要
//   file    work 会话 → C:\deepseek\work\handover\selfcheck\<at>.json
//           其它工作区 → <当前工作区>\work\handover\selfcheck\<at>.json
//           （自动与同目录上一份做差分；不同工作区各存各的，互不污染基线）
//
// 说明：
//   1. 用运行时自带的 node（C:\Users\ZQY\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe）
//   2. 只用 Node 内置模块，零依赖；记忆库用内置 node:sqlite 只读打开
//   3. 冒烟调用（工具面）无法在进程外完成，脚本只做「进程内能证明」的部分，
//      并把需要对话侧真调一遍的动作列在 smoke.manual 里

import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { execFileSync, spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { DatabaseSync } from 'node:sqlite';

// ── 路径常量：环境变量优先，换机器不用改代码 ────────────────────────
//   SELFCHECK_HOME     用户主目录（默认 %USERPROFILE%）
//   DSH_HOME           DSH 数据根（默认 <HOME>/.dsh）
//   DSH_PROFILE        profile 名（默认 desktop）
//   SELFCHECK_WORK     工作区根（默认 C:\deepseek\work）
//   SELFCHECK_PLUGINS  插件归档目录（默认 C:\deepseek\插件）
//   SELFCHECK_DSH_CMD  内核 cli 的 dsh.cmd
//   SELFCHECK_EXE      桌面外壳 exe
// 一个都没设时，下面这些默认值就是作者机器的实际路径。
const HOME = process.env.SELFCHECK_HOME || process.env.USERPROFILE || 'C:\\Users\\ZQY';
const DSH_HOME = process.env.DSH_HOME || path.join(HOME, '.dsh');
const PROFILE = path.join(DSH_HOME, 'profiles', process.env.DSH_PROFILE || 'desktop');
const WORK = process.env.SELFCHECK_WORK || 'C:\\deepseek\\work';
// 取数口径：当前会话工作区（含 .dsh-mind 或旧 .dsh-meow 就以 cwd 为准，否则退回 work）
const WS =
  fs.existsSync(path.join(process.cwd(), '.dsh-mind')) || fs.existsSync(path.join(process.cwd(), '.dsh-meow'))
    ? process.cwd()
    : WORK;
const PLUGDIR = process.env.SELFCHECK_PLUGINS || 'C:\\deepseek\\插件';
// 2026-11-20 起记忆插件换成 meow-mind，库目录 .dsh-mind；旧 .dsh-meow 只作回滚保留
const MEMDB = fs.existsSync(path.join(WS, '.dsh-mind', 'memory.db'))
  ? path.join(WS, '.dsh-mind', 'memory.db')
  : path.join(WS, '.dsh-meow', 'memory.db');
const OUTDIR =
  WS === WORK ? path.join(WORK, 'handover', 'selfcheck') : path.join(WS, 'work', 'handover', 'selfcheck');
const DSH_CMD = process.env.SELFCHECK_DSH_CMD || 'C:\\deepseek\\官方\\resources\\runtime\\cli\\bin\\dsh.cmd';
const EXE = process.env.SELFCHECK_EXE || 'C:\\deepseek\\官方\\DeepSeek Harness.exe';

const MODE = process.argv.includes('--quick') ? 'quick' : 'full';
const ONLY_DIFF = process.argv.includes('--diff');
// --only 06,08 → 只跑这几项（项号补零，接受 6 或 06）
const ONLY = (() => {
  const i = process.argv.indexOf('--only');
  if (i < 0) return null;
  const ids = String(process.argv[i + 1] || '').split(',').map((s) => s.trim()).filter(Boolean);
  if (!ids.length) return null;
  return new Set(ids.map((s) => {
    const n = s.replace(/\D/g, '').padStart(2, '0');
    return n === '11' ? '03' : n;   // 11 更新检查已并入 03（四态判定），旧命令继续能用
  }));
})();
const want = (id) => !ONLY || ONLY.has(id);

// ── 清理名单（不靠临场判断） ────────────────────────────────────────────
const SAFE_TO_CLEAN = [
  'C:\\deepseek\\插件\\archives（旧 tgz 安装包，装完即可清）',
  'C:\\Users\\ZQY\\.dsh\\storages\\pdf-reader 下的旧封面/临时目录',
  'C:\\Users\\ZQY\\.dsh\\attachments 里已删会话的残留（每次 API 上传的 PDF 副本，删会话不回收）',
  `${WS}\\.dsh-mind\\memory.db.bak 与 ${WS}\\.dsh-meow\\memory.db.bak 及 *.bak（升级前备份，确认无误后可清）`,
  'C:\\Users\\ZQY\\.dsh\\logs 下 7 天前的日志',
  `${OUTDIR} 下 30 天前的 json`,
];
const DO_NOT_TOUCH = [
  'C:\\deepseek\\插件\\dsh-raw-html-v2（活引用 clone，插件本体）',
  'C:\\deepseek\\tools\\mineru3-test\\venv（MinerU 常驻 API 的运行时）',
  'C:\\deepseek\\tools\\sci-venv（科学计算环境）',
];

// ── 小工具 ───────────────────────────────────────────────────────────
function sh(cmd) {
  try {
    return execFileSync('powershell.exe', ['-NoProfile', '-Command', cmd], {
      encoding: 'utf8', timeout: 60000, windowsHide: true,
    }).trim();
  } catch (e) {
    return `ERR ${e.status ?? '?'}: ${String(e.stderr || e.message).slice(0, 200)}`;
  }
}
function readJson(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; }
}
function walk(dir, acc = { files: 0, bytes: 0 }) {
  let ents;
  try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch { return acc; }
  for (const e of ents) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, acc);
    else if (e.isFile()) {
      acc.files++;
      try { acc.bytes += fs.statSync(p).size; } catch {}
    }
  }
  return acc;
}
function dirStat(p) {
  const r = walk(p);
  return { files: r.files, mb: +(r.bytes / 1048576).toFixed(1) };
}
function mtime(p) {
  try { return fs.statSync(p).mtime; } catch { return null; }
}
function daysAgo(d) {
  if (!d) return null;
  return Math.floor((Date.now() - d.getTime()) / 86400000);
}
function portListening(port) {
  const out = sh(`(Get-NetTCPConnection -LocalPort ${port} -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count`);
  return out === '1' ? true : out === '0' ? false : null;
}
function httpPing(url) {
  // 只用同步方式：curl.exe 在 Windows 10+ 自带
  const out = sh(`(curl.exe -s -o NUL -w "%{http_code}" --max-time 2 "${url}")`);
  return /^\d{3}$/.test(out) ? +out : null;
}

// ── 01 内核 ─────────────────────────────────────────────────────────
function kernel() {
  const cli = sh(`& "${DSH_CMD}" --version 2>$null`);
  const exeVersion = sh(`(Get-Item "${EXE}").VersionInfo.FileVersion`);
  const electron = fs.existsSync('C:\\deepseek\\官方\\version')
    ? fs.readFileSync('C:\\deepseek\\官方\\version', 'utf8').trim() : null;
  return { cli: cli.replace(/\s+/g, ' ').trim(), exe: exeVersion, electron, match: cli.includes(exeVersion) && !!exeVersion };
}

// ── 02 依赖 ─────────────────────────────────────────────────────────
function profileDeps() {
  const pkg = readJson(path.join(PROFILE, 'package.json'));
  if (!pkg) return { error: 'package.json 读不到' };
  const deps = Object.entries(pkg.dependencies || {}).map(([n, v]) => ({ name: n, spec: v }));
  const bundles = pkg.dsh?.profile?.bundles || [];
  const bundleSet = new Set(bundles);
  // bundles 里可能是包名，也可能是「包名/子路径」；用前缀匹配
  const missing = deps.filter(d => !bundles.some(b => b === d.name || b.startsWith(d.name + '/'))).map(d => d.name);
  // 内核自带的 bundle（@deepseek-ai/*）不在 dependencies 里属正常，不算「多余」
  const extra = bundles.filter(b => !b.startsWith('@deepseek-ai/') && !deps.some(d => b === d.name || b.startsWith(d.name + '/')));
  return { count: deps.length, bundles: bundles.length, missingInBundles: missing, extraInBundles: extra };
}

// ── 03 三方插件 ──────────────────────────────────────────────────────
const PURPOSE = {
  'dsh-better-sidebar': '侧边栏 / 会话管理',
  'dsh-context': '会话上下文与子代理驾驶舱',
  'billion-context': 'ACP 上下文压缩（上游包）',
  'meow-mind': '跨会话长期记忆（自研：22 工具 / schema 5 + 关系网 + 自动捕获 + /dream 指令 + 沉淀候选）',
  'dsh-univer-office': 'Univer 文档 / 表格 / 幻灯片 / 数据库 / 画布',
  'dsh-raw-html-v2': '裸 HTML 卡片渲染（VCP 美学）',
  'dsh-doc-parser': '通用文档解析（doc_info / doc_text / doc_render / doc_ocr / doc_tables / doc_parse / doc_formulas）',
  'bili-vision': 'B站视频画面理解 / 抽帧',
  'dsh-research-toolkit': '科研软件桥接',
  'cc-safety-net': '运行时拦破坏性命令与密钥文件',
  'dsh-auth-cookie-sweep': 'cookie 清理（防请求头超限）',
  '@liustack/modsearch': '网页 / X 检索桥',
  '@wxg-prc-cpg/browser-skill-dsh-plugin': '登录态浏览器自动化',
  '@ericwang1358/dsh-daily-flashcard': 'StudyHub 学习工作区',
  'dsh-hot-installer': '插件热装载',
  'dsh-power-menu': '右上角电源键',
  'dsh-whale-widget': '余额小鲸鱼浮窗',
  'dsh-plugin-structured-prompt': '结构化提示词表单',
  'dsh-prompt-rewriter': '输入框旁一键改写草稿（不发送）',
  'dsh-history-viewer': '历史会话查看',
  'dsh-step-pause': '步进暂停',
  'dsh-visual-card': '可视化交互卡（iframe 跑脚本）',
  '@smalltailqwq/dsh-client-ui-skin-deep-whale-manager': '皮肤 · 深鲸管理',
  '@smalltailqwq/dsh-client-ui-skin-maid-atelier': '皮肤 · 女仆工坊',
  '@smalltailqwq/dsh-client-ui-skin-orca-link': '皮肤 · 虎鲸链路',
};
const NPM_REG = process.env.SELFCHECK_REGISTRY || 'https://registry.npmmirror.com';
function cmpVer(a, b) {
  const pa = String(a).split(/[.-]/).map((x) => parseInt(x, 10) || 0);
  const pb = String(b).split(/[.-]/).map((x) => parseInt(x, 10) || 0);
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const x = pa[i] ?? 0, y = pb[i] ?? 0;
    if (x !== y) return x < y ? -1 : 1;
  }
  return 0;
}
// 2026-11-24 起：版本列带「是否最新」判定——registry 有同版本写「新」，有新版写「旧 → x.y.z」，
// 查不到（自建 / link / git 私有）写「本地」。查的是 registry latest，不是 dist-tags 里的预发布。
// 同日补：registry 查不到的（file:/link:/git 装）再按 package.json 的 repository 去 jsdelivr 查
// GitHub tag（`data.jsdelivr.com` 国内可直连，不用开代理）；无仓库写「自研」，有仓库无 tag 写「无 tag」。
async function npmLatest(name) {
  try {
    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), 5000);
    const r = await fetch(`${NPM_REG}/${name}/latest`, { signal: ac.signal, headers: { accept: 'application/json' } });
    clearTimeout(t);
    if (!r.ok) return null;
    const j = await r.json();
    return typeof j?.version === 'string' ? j.version : null;
  } catch { return null; }
}
function parseGithubRepo(repo) {
  if (!repo) return null;
  const s = String(repo).replace(/^git\+/, '').replace(/\.git$/, '');
  const m = s.match(/github\.com[/:]([^/]+)\/([^/]+)/i);
  return m ? `${m[1]}/${m[2]}` : null;
}
async function ghTags(full) {
  try {
    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), 6000);
    const r = await fetch(`https://data.jsdelivr.com/v1/packages/gh/${full}`, { signal: ac.signal, headers: { accept: 'application/json' } });
    clearTimeout(t);
    if (!r.ok) return null;
    const j = await r.json();
    const vs = (j.versions || []).map((v) => String(v.version).replace(/^v/, '')).filter(Boolean);
    return vs.length ? vs : null;
  } catch { return null; }
}
async function plugins(deps) {
  const out = [];
  for (const { name, spec } of deps) {
    const p = path.join(PROFILE, 'node_modules', ...name.split('/'), 'package.json');
    const j = readJson(p);
    const repo = j?.repository;
    out.push({
      name,
      version: j?.version ?? 'MISSING',
      purpose: PURPOSE[name] ?? (j?.description ? String(j.description).slice(0, 40) : '—'),
      repo: typeof repo === 'string' ? repo : (repo?.url || ''),
      // git 装的也算第三方源：bili-vision 是 git+gh-proxy，被误判成 registry 后去查 npm 只会 404
      source: spec.startsWith('link:') ? 'link'
        : spec.startsWith('file:') ? 'file'
        : /^(git\+|github:|gitlab:|bitbucket:|https?:\/\/\S+\.git)/.test(spec) ? 'git'
        : 'registry',
    });
  }
  await Promise.all(out.map(async (p) => {
    // ① 先查 registry（0.2 秒级）
    const latest = await npmLatest(p.name);
    if (latest) {
      p.latest = latest;
      p.update = cmpVer(p.version, latest) >= 0 ? '新' : `旧 → ${latest}`;
      return;
    }
    // ② registry 没有 → 按 repository 查 GitHub tag（jsdelivr 直连，不需要代理）
    const full = parseGithubRepo(p.repo);
    if (!full) { p.update = '自研'; return; }
    const tags = await ghTags(full);
    if (!tags) { p.update = '无 tag'; return; }
    const best = tags.reduce((m, v) => (cmpVer(v, m) > 0 ? v : m), tags[0]);
    p.latest = best;
    p.update = cmpVer(p.version, best) >= 0 ? '新' : `旧 → ${best}`;
  }));
  return out.sort((a, b) => a.name.localeCompare(b.name));
}

// ── 04 插件目录 ──────────────────────────────────────────────────────
function plugDirs() {
  const subs = ['archives', 'backups', 'forks', 'patches', 'dsh-raw-html-v2'];
  const o = {};
  for (const s of subs) {
    const p = path.join(PLUGDIR, s);
    o[s] = fs.existsSync(p) ? dirStat(p) : null;
  }
  o.total = dirStat(PLUGDIR);
  return o;
}

// ── 05 B站 MCP ──────────────────────────────────────────────────────
async function biliMcpSmoke() {
  const base = 'C:\\deepseek\\tools\\bili-mcp';
  let entry;
  try {
    const require = createRequire(path.join(base, 'package.json'));
    entry = require.resolve('bilibili-mcp-server');
  } catch (e) {
    return { ok: false, error: `cannot resolve server: ${String(e.message).slice(0, 80)}` };
  }
  const child = spawn(process.execPath, [entry], {
    env: { ...process.env, BILIBILI_COOKIE_FILE: path.join(base, 'cookie.json') },
    stdio: ['pipe', 'pipe', 'ignore'],
    windowsHide: true,
  });
  let buf = '';
  const pending = new Map();
  child.stdout.on('data', (d) => {
    buf += d.toString();
    let i;
    while ((i = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, i).trim();
      buf = buf.slice(i + 1);
      if (!line) continue;
      let msg; try { msg = JSON.parse(line); } catch { continue; }
      if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
    }
  });
  const send = (id, method, params) => new Promise((res) => {
    pending.set(id, res);
    try { child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n'); } catch {}
    setTimeout(() => { if (pending.has(id)) { pending.delete(id); res({ timeout: true }); } }, 15000);
  });
  try {
    await send(1, 'initialize', { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'selfcheck', version: '1' } });
    try { child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n'); } catch {}
    const list = await send(2, 'tools/list', {});
    const tools = list.result?.tools ?? [];
    const r = await send(3, 'tools/call', { name: 'bilibili_video_info', arguments: { videoId: 'BV1mExE6AEJD' } });
    const ok = r.result?.isError !== true && !!r.result?.content?.[0]?.text;
    const head = (r.result?.content?.[0]?.text || JSON.stringify(r).slice(0, 120)).split('\n')[0].slice(0, 60);
    return { ok, toolCount: tools.length, sample: head, names: tools.map(t => t.name) };
  } finally {
    try { child.kill(); } catch {}
  }
}

async function bili() {
  const dir = 'C:\\deepseek\\tools\\bili-mcp';
  const cookie = path.join(dir, 'cookie.json');
  const m = mtime(cookie);
  const smoke = await biliMcpSmoke();
  return {
    server: fs.existsSync(dir),
    cookieMtime: m ? m.toISOString().slice(0, 19).replace('T', ' ') : null,
    cookieDaysAgo: daysAgo(m),
    mcp: smoke,
  };
}

// ── 06 技能 ─────────────────────────────────────────────────────────
// 读 frontmatter 里的 description 与 disable-model-invocation：
// 目录开销按 description 全长算，但 disable-model-invocation: true 的技能连简介都不进上下文 → 记 0。
function fmValue(fm, key) {
  const re = new RegExp('^' + key + ':\\s*([\\s\\S]*?)(?=\\n[A-Za-z][A-Za-z0-9_-]*:\\s|\\n---|$)', 'm');
  const m = fm.match(re);
  return m ? m[1].replace(/\s+/g, ' ').trim().replace(/^["']|["']$/g, '') : null;
}
function skillMeta(f) {
  try {
    const t = fs.readFileSync(f, 'utf8');
    const m = t.match(/^---\r?\n([\s\S]*?)\r?\n---/);
    const fm = m ? m[1] : '';
    const desc = (fmValue(fm, 'description') || '').replace(/^[>|]\s*/, '');
    const disabled = /^disable-model-invocation:\s*true\s*$/m.test(fm);
    const keys = [...fm.matchAll(/^([A-Za-z][A-Za-z0-9_-]*):/gm)].map((x) => x[1]);
    // 只报「可能有权限含义或未知」的键；author / version / license / whenToUse 是本机自建技能的惯例写法
    const SAFE_FM = ['name', 'description', 'author', 'version', 'license', 'whenToUse', 'tags', 'metadata'];
    return { descChars: disabled ? 0 : desc.length, disabled, extraKeys: keys.filter((k) => !SAFE_FM.includes(k)) };
  } catch { return { descChars: 0, disabled: false, extraKeys: [] }; }
}
function skills() {
  const userDir = path.join(HOME, '.agents', 'skills');
  const user = [];
  try {
    for (const e of fs.readdirSync(userDir, { withFileTypes: true })) {
      if (!e.isDirectory()) continue;
      const f = path.join(userDir, e.name, 'SKILL.md');
      if (fs.existsSync(f)) user.push({ name: e.name, kb: +(fs.statSync(f).size / 1024).toFixed(1), ...skillMeta(f) });
    }
  } catch {}
  // 插件自带（扫 node_modules 下所有 SKILL.md，最多三层）
  const plug = [];
  const root = path.join(PROFILE, 'node_modules');
  const scan = (d, depth) => {
    if (depth > 4) return;
    let ents; try { ents = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of ents) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) { if (e.name !== 'node_modules') scan(p, depth + 1); }
      else if (e.name === 'SKILL.md') {
        const rel = path.relative(root, d).replace(/\\/g, '/');
        const pkg = rel.startsWith('@') ? rel.split('/').slice(0, 2).join('/') : rel.split('/')[0];
        plug.push({ pkg, skill: path.basename(d), ...skillMeta(p) });
      }
    }
  };
  scan(root, 0);
  const byPkg = {};
  for (const s of plug) (byPkg[s.pkg] ||= []).push(s.skill);
  // 同名不同目录会静默覆盖（先扫到的赢）：插件内同名更常见，跨 user/插件也可能撞
  const nameCount = {};
  for (const s of [...user, ...plug]) { const n = s.name || s.skill; nameCount[n] = (nameCount[n] || 0) + 1; }
  const dupNames = Object.entries(nameCount).filter(([, n]) => n > 1).map(([k]) => k);
  // 目录开销估算：name + description（`<available_skills>` 模板本身另算）
  const catalogChars = [...user, ...plug].reduce((a, s) => a + (s.name || s.skill).length + s.descChars, 0);
  return { user, pluginCount: plug.length, byPkg, dupNames, catalogChars };
}

// ── 12 使用统计（近 30 天会话日志，只读）─────────────────────────────
// 工具名前缀 → 插件。手写映射，加插件时补一行；没命中的算「内核 / 其它」。
const TOOL_OWNER = [
  [/^memory_/, 'meow-mind'],
  [/^univer_/, 'dsh-univer-office'],
  [/^(doc_|pdf_)/, 'dsh-doc-parser'],
  [/^study_/, 'dsh-daily-flashcard'],
  [/^a2ui/, 'dsh-a2ui'],
  [/^(bilibili_|bili_)/, 'bili-vision'],
  [/^(web_search|web_fetch|read_page|x_search)$/, '@liustack/modsearch'],
  [/^research_/, 'dsh-research-toolkit'],
  [/^(bsk_|browser_)/, 'browser-skill'],
  [/^render_visual$/, 'dsh-visual-card'],
  [/^(build_structured_prompt|structured_prompt)$/, 'dsh-plugin-structured-prompt'],
  [/^(compress|decompress|search_context|acp_status|acp_cache|acp_read_original_image)$/, 'billion-context'],
];
const ownerOf = (n) => (TOOL_OWNER.find(([re]) => re.test(n)) || [])[1] || null;

// 会话日志是「多帧拼接」的 zstd（每批写入一帧）；Node 的 zstd 流只解第一帧，
// 所以按 magic 切帧后逐帧解——2026-11-24 实测 88 MB / 51780 帧全解出、零失败。
const ZSTD_MAGIC = Buffer.from([0x28, 0xb5, 0x2f, 0xfd]);
async function* sessionLines(p) {
  const buf = fs.readFileSync(p);
  if (!/\.zst(d)?$/i.test(p)) { for (const line of buf.toString('utf8').split('\n')) if (line) yield line; return; }
  const pos = [];
  let i = 0;
  while ((i = buf.indexOf(ZSTD_MAGIC, i)) !== -1) { pos.push(i); i += 4; }
  for (let k = 0; k < pos.length; k++) {
    const end = k + 1 < pos.length ? pos[k + 1] : buf.length;
    let text;
    try { text = zlib.zstdDecompressSync(buf.subarray(pos[k], end)).toString('utf8'); } catch { continue; }
    for (const line of text.split('\n')) if (line) yield line;
  }
}

async function usage(days = 30) {
  const root = path.join(DSH_HOME, 'sessions');
  const cutoff = Date.now() - days * 86400000;
  const files = [];
  const walkU = (d) => {
    let ents; try { ents = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of ents) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) walkU(p);
      else if (/^session.*\.jsonl(\.zst(d)?)?$/i.test(e.name)) {
        try { if (fs.statSync(p).mtimeMs >= cutoff) files.push(p); } catch {}
      }
    }
  };
  walkU(root);
  files.sort((a, b) => fs.statSync(a).mtimeMs - fs.statSync(b).mtimeMs);

  const skillsUse = {};      // name → [manual, auto, last]
  const ownerCalls = {};     // 插件 → 调用次数
  const toolTop = {};        // 工具名 → 次数
  let sessions = 0, events = 0, header = null, minHeader = null, catalogChars = null;
  const stamp = (v) => {
    const t = typeof v === 'number' ? (v > 1e12 ? v : v * 1000) : Date.parse(v);
    return t ? new Date(t).toISOString().slice(0, 10) : null;
  };
  const bump = (map, k, i, day) => {
    const rec = (map[k] ||= [0, 0, null]);
    if (i >= 0) rec[i]++;
    if (day && (!rec[2] || day > rec[2])) rec[2] = day;
  };

  for (const f of files) {
    sessions++;
    try {
      for await (const line of sessionLines(f)) {
        if (!line.includes('"tool/call"') && !line.includes('"user/message"') && !line.includes('"request/header"')) continue;
        let o; try { o = JSON.parse(line); } catch { continue; }
        const day = stamp(o.time);
        if (o.type === 'tool/call') {
          events++;
          const t = o.data || {};
          if (t.name === 'skill') {
            let n = null;
            try { n = JSON.parse(t.arguments || '{}').name; } catch {}
            if (n) bump(skillsUse, n, 1, day);
          } else if (t.name) {
            toolTop[t.name] = (toolTop[t.name] || 0) + 1;
            const who = ownerOf(t.name) || '内核 / 其它';
            ownerCalls[who] = (ownerCalls[who] || 0) + 1;
          }
        } else if (o.type === 'user/message') {
          for (const c of o.data?.content || []) {
            const x = c?.text; if (!x) continue;
            if (x.includes('<skill_content')) {
              for (const m of x.matchAll(/<skill_content\s+name="([^"]+)"/g)) { events++; bump(skillsUse, m[1], 0, day); }
            }
            if (x.includes('<available_skills>')) { events++; catalogChars = x.length; }
          }
        } else if (o.type === 'request/header') {
          const tools = o.data?.header?.tools;
          if (Array.isArray(tools) && tools.length) {
            events++;
            // 工具面随会话漂移（MCP 没起、插件没注册），留最全与最省两档，别取最后一次
            const chars = JSON.stringify(tools).length;
            // MCP 单独拆账：DSH 默认把 MCP 工具说明全量塞进上下文，是最容易失控的一块
            const mcp = tools.filter((t) => String(t?.name || t?.function?.name || '').startsWith('mcp__'));
            const mcpChars = mcp.length ? JSON.stringify(mcp).length : 0;
            const rec = { tools: tools.length, chars, mcpTools: mcp.length, mcpChars };
            if (!header || chars > header.chars) header = rec;
            if (!minHeader || chars < minHeader.chars) minHeader = rec;
          }
        }
      }
    } catch { /* 单文件解压失败就跳过，不中断整轮 */ }
  }

  // 活跃技能目录（与 06 段同口径），用来算「零触发」；按 description 字符降序——贵又没人用的排前面
  const userSkills = skills().user;
  const descOf = (n) => userSkills.find((s) => s.name === n)?.descChars || 0;
  const activeSkills = userSkills.map((s) => s.name);
  const idleSkills = activeSkills.filter((n) => !skillsUse[n]).sort((a, b) => descOf(b) - descOf(a));
  const idleOwners = [...new Set(TOOL_OWNER.map(([, w]) => w))].filter((w) => !ownerCalls[w]);
  const top = Object.entries(toolTop).sort((a, b) => b[1] - a[1]).slice(0, 12);

  // 硬闸门：扫了会话却识别 0 事件，多半是日志格式变了——此时「没人用」的结论不可信，必须喊停
  const gate = sessions >= 5 && events === 0
    ? `扫到 ${sessions} 个会话但识别 0 事件：日志格式可能已变，本次用量结论不可用`
    : null;

  // user-global AGENTS.md 也在每个请求付费，但此前从没进过体检表
  let agentsMdChars = 0;
  try { agentsMdChars = fs.readFileSync(path.join(DSH_HOME, 'AGENTS.md'), 'utf8').length; } catch {}

  return {
    days, sessions, events,
    gate,
    overhead: header ? { tools: header.tools, chars: header.chars, minTools: minHeader?.tools ?? header.tools, minChars: minHeader?.chars ?? header.chars, mcpTools: header.mcpTools ?? 0, mcpChars: header.mcpChars ?? 0, skillCatalogChars: catalogChars } : null,
    agentsMdChars,
    skillsUsed: Object.fromEntries(Object.entries(skillsUse).sort((a, b) => (b[1][1] + b[1][0]) - (a[1][1] + a[1][0]))),
    descChars: Object.fromEntries(activeSkills.map((n) => [n, descOf(n)])),
    ownerCalls: Object.fromEntries(Object.entries(ownerCalls).sort((a, b) => b[1] - a[1])),
    toolTop: top,
    idleSkills,
    idleOwners,
  };
}

// ── 07 长期记忆 ─────────────────────────────────────────────────────
function memory() {
  if (!fs.existsSync(MEMDB)) return { error: 'memory.db 不存在' };
  try {
    const db = new DatabaseSync(MEMDB, { readOnly: true });
    const q = (sql) => db.prepare(sql).all();
    const tables = ['soul', 'user', 'project', 'fact', 'lesson', 'topic', 'rules'];
    const byLevel = {};
    let active = 0, all = 0;
    for (const t of tables) {
      try {
        const r = q(`SELECT COUNT(*) c, SUM(status IN ('active','memory','evolution')) a FROM ${t}`)[0];
        byLevel[t] = { active: r.a ?? 0, all: r.c ?? 0 };
        active += r.a ?? 0; all += r.c ?? 0;
      } catch {}
    }
    let longest = [];
    try {
      longest = q(`SELECT id, level, status, length(content) n FROM (
          SELECT id,'fact' level,status,content FROM fact
          UNION ALL SELECT id,'lesson',status,content FROM lesson
          UNION ALL SELECT id,'topic',status,content FROM topic
        ) WHERE status IN ('active','memory','evolution') ORDER BY n DESC LIMIT 3`);
    } catch {}
    // 超长条目计数：>800 字为高优先（体检应先压），>450 为一般
    let over = { n800: 0, n450: 0 };
    try {
      const o = q(`SELECT SUM(n>800) a, SUM(n>450) b FROM (
          SELECT length(content) n FROM user WHERE status IN ('active','memory','evolution')
          UNION ALL SELECT length(content) FROM project WHERE status IN ('active','memory','evolution')
          UNION ALL SELECT length(content) FROM fact WHERE status IN ('active','memory','evolution')
          UNION ALL SELECT length(content) FROM lesson WHERE status IN ('active','memory','evolution')
          UNION ALL SELECT length(content) FROM topic WHERE status IN ('active','memory','evolution')
          UNION ALL SELECT length(content) FROM rules WHERE status IN ('active','memory','evolution')
        )`)[0];
      over = { n800: o.a ?? 0, n450: o.b ?? 0 };
    } catch {}
    db.close();
    const wal = fs.existsSync(MEMDB + '-wal') ? +(fs.statSync(MEMDB + '-wal').size / 1048576).toFixed(1) : 0;
    return { dbPath: MEMDB, active, all, byLevel, longest, over, walMB: wal, sizeMB: +(fs.statSync(MEMDB).size / 1048576).toFixed(2) };
  } catch (e) {
    return { error: String(e.message).slice(0, 200) };
  }
}

// 沉淀候选：直接复用 meow-mind 的 findSinkCandidates，避免两套判据漂移。
// 判据读 ~/.agents/skills/*/SKILL.md 算重合率：>0.5 视为已写进技能而排除，0.12–0.5 记为提示去向。
// 插件侧另用 findPluginGaps：记忆里提到的代码符号在所有自建插件源码里都找不到 → 可能是插件该补的能力。
// 插件没装或加载失败只报 error/skipped，不影响自检其余项。
async function sinkCandidates() {
  try {
    const srcDir = path.join(PROFILE, 'node_modules', 'meow-mind', 'src');
  const src = path.join(srcDir, 'store.mjs');
    if (!fs.existsSync(src)) return { skipped: 'meow-mind 未安装' };
    const { findSinkCandidates } = await import(pathToFileURL(src).href);
  const { findPluginGaps } = await import(pathToFileURL(path.join(srcDir, 'plugins.mjs')).href);
    const db = new DatabaseSync(MEMDB, { readOnly: true });
    try {
      const r = findSinkCandidates(db, 3, 1);
      let gaps = null;
      try {
        const g = findPluginGaps(db, 3, 7);
        gaps = { total: g.total ?? 0, plugins: g.plugins ?? [], skipped: g.skipped, items: (g.items || []).map((i) => i.symbol) };
      } catch (e) { gaps = { error: String(e && e.message ? e.message : e).slice(0, 120) }; }
      return {
        total: r.total ?? 0,
        preview: (r.items || []).map((i) => ({ id: i.id, level: i.level, chars: i.chars, hint: i.hintSkill ?? '未匹配' })),
        pluginGaps: gaps,
      };
    } finally { db.close(); }
  } catch (e) {
    return { error: String(e && e.message ? e.message : e).slice(0, 150) };
  }
}

// ── 08 工作区 ───────────────────────────────────────────────────────
function workspace() {
  const o = { root: WS, total: dirStat(WS) };
  try {
    o.children = {};
    for (const e of fs.readdirSync(WS, { withFileTypes: true })) {
      if (!e.isDirectory()) continue;
      const st = dirStat(path.join(WS, e.name));
      // 2026-11-13：不使用 work 专用白名单，全量子目录里挑显著的（≥20 MB 或 ≥200 文件）。
      // 原白名单让非 work 工作区的大部分体积不可见（study 曾漏报 7.3 GB）。
      if (st.mb >= 20 || st.files >= 200) o.children[e.name] = st;
    }
  } catch {}
  return o;
}

// ── 09 HOME ─────────────────────────────────────────────────────────
function home_() {
  const o = { total: dirStat(DSH_HOME) };
  try {
    o.children = {};
    for (const e of fs.readdirSync(DSH_HOME, { withFileTypes: true })) {
      if (e.isDirectory()) o.children[e.name] = dirStat(path.join(DSH_HOME, e.name));
    }
  } catch {}
  return o;
}

// ── 10 外部通道与后台 ────────────────────────────────────────────────
function external(deps) {
  const names = deps.map(d => d.name);
  const guiPorts = sh(`(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -in (Get-Process -Name 'DeepSeek Harness','DeepSeek*' -ErrorAction SilentlyContinue).Id } | Select-Object -ExpandProperty LocalPort -Unique) -join ','`);
  return {
    qqPlugin: names.includes('dsh-qqbot-bridge'),
    qqCreds: fs.existsSync(path.join(DSH_HOME, '.credentials.yaml')),
    mineruPort18000: portListening(18000),
    mineruHttp: httpPing('http://127.0.0.1:18000/openapi.json'),
    bskDaemon: portListening(52800) || portListening(52801) || portListening(52802),
    guiPorts: guiPorts || null,
    worktrees: (() => {
      const out = [];
      try {
        for (const e of fs.readdirSync(WS, { withFileTypes: true }))
          if (e.isDirectory() && (e.name.startsWith('.tmp') || e.name.includes('-OLD'))) out.push(e.name);
      } catch {}
      return out;
    })(),
    schedule: '在对话侧用 schedule_list 读（脚本无宿主上下文）',
  };
}

// ── 差分 ────────────────────────────────────────────────────────────
function loadPrev() {
  try {
    const files = fs.readdirSync(OUTDIR).filter(f => f.endsWith('.json')).sort();
    if (!files.length) return null;
    const last = files[files.length - 1];
    return { file: last, data: readJson(path.join(OUTDIR, last)) };
  } catch { return null; }
}
function diff(prev, cur) {
  if (!prev?.data) return { note: '首次运行，无基线' };
  const p = prev.data;
  const d = { baseline: prev.file };
  // 版本差分
  const pv = Object.fromEntries((p.plugins || []).map(x => [x.name, x.version]));
  const cv = Object.fromEntries((cur.plugins || []).map(x => [x.name, x.version]));
  const changed = [], added = [], removed = [];
  for (const [n, v] of Object.entries(cv)) {
    if (!(n in pv)) added.push(`${n}@${v}`);
    else if (pv[n] !== v) changed.push(`${n} ${pv[n]}→${v}`);
  }
  for (const n of Object.keys(pv)) if (!(n in cv)) removed.push(n);
  // 依赖 / bundles 数量
  const counts = [];
  if (p.deps?.count !== cur.deps?.count) counts.push(`依赖 ${p.deps?.count}→${cur.deps?.count}`);
  if (p.deps?.bundles !== cur.deps?.bundles) counts.push(`bundles ${p.deps?.bundles}→${cur.deps?.bundles}`);
  if (p.kernel?.cli !== cur.kernel?.cli) counts.push(`内核 ${p.kernel?.cli}→${cur.kernel?.cli}`);
  // 体积（只比全检）
  const vols = [];
  if (p.home?.total && cur.home?.total) {
    const dmb = +(cur.home.total.mb - p.home.total.mb).toFixed(1);
    if (Math.abs(dmb) >= 100) vols.push(`.dsh ${p.home.total.mb}→${cur.home.total.mb} MB (${dmb > 0 ? '+' : ''}${dmb})`);
  }
  if (p.workspace?.total && cur.workspace?.total) {
    const dmb = +(cur.workspace.total.mb - p.workspace.total.mb).toFixed(1);
    if (Math.abs(dmb) >= 20) vols.push(`工作区 ${p.workspace.total.mb}→${cur.workspace.total.mb} MB (${dmb > 0 ? '+' : ''}${dmb})`);
  }
  // 记忆
  const mem = [];
  if (p.memory?.active != null && cur.memory?.active != null) {
    const dm = cur.memory.active - p.memory.active;
    if (dm) mem.push(`活跃记忆 ${p.memory.active}→${cur.memory.active} (${dm > 0 ? '+' : ''}${dm})`);
  }
  return { baseline: prev.file, changed, added, removed, counts, vols, mem };
}

// ── 主流程 ──────────────────────────────────────────────────────────
const t0 = Date.now();
function nowLocal() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

function depArray() {
  const pkg = readJson(path.join(PROFILE, 'package.json'));
  return Object.entries(pkg?.dependencies || {}).map(([name, spec]) => ({ name, spec }));
}

const result = { at: nowLocal(), mode: MODE, host: 'selfcheck.mjs' };
if (ONLY) result.only = [...ONLY];
const deps = want('02') ? profileDeps() : null;
if (want('01')) result.kernel = kernel();
if (want('02')) result.deps = deps;
if (want('03')) result.plugins = await plugins(depArray());
if (MODE === 'full' || ONLY) {
  if (want('04')) result.plugDirs = plugDirs();
  if (want('05')) result.bili = await bili();
  if (want('06')) result.skills = skills();
  if (want('08')) result.workspace = workspace();
  if (want('09')) result.home = home_();
}
if (want('07')) {
  result.memory = memory();
  result.memory.sink = await sinkCandidates();
}
if (want('10')) result.external = external(depArray());
if (want('12') && (MODE === 'full' || ONLY)) result.usage = await usage();

// 清理名单
result.clean = { safeToClean: SAFE_TO_CLEAN, doNotTouch: DO_NOT_TOUCH };

// 冒烟：脚本能证明的 + 需要对话侧做的
result.smoke = {
  auto: {
    memoryDbReadable: result.memory ? !!result.memory.active : 'skipped',
    kernelCliWorks: result.kernel ? !String(result.kernel.cli).startsWith('ERR') : 'skipped',
    mineruUp: result.external ? result.external.mineruPort18000 === true : 'skipped',
  },
  manual: [
    'memory_search 查一条旧事实（如「DSHM 平板 HoKit」）能召回',
    '本轮记忆注入横条可见',
    'univer_* 工具在工具面即可（禁止新建探针文件：会弹文档窗且被服务锁死）',
    'QQ 侧真发一条消息看是否回',
    'schedule_list 看定时任务是否在',
  ],
};

// 差分（--only 不是完整快照，不参与基线比对）
const prev = ONLY ? null : loadPrev();
result.diff = ONLY ? { note: '--only 模式：不落档、不做差分' } : diff(prev, result);

// 落档（--only 不写文件，免得污染下一轮 full 的基线）
let outFile = '（--only 模式，不落档）';
if (!ONLY) {
  fs.mkdirSync(OUTDIR, { recursive: true });
  const stamp = result.at.replace(/[: ]/g, '-');
  outFile = path.join(OUTDIR, `${stamp}-${MODE}.json`);
  fs.writeFileSync(outFile, JSON.stringify(result, null, 2), 'utf8');
}

// ── 输出 ────────────────────────────────────────────────────────────
const L = [];
const tag = MODE + (ONLY ? ` only=${[...ONLY].sort().join(',')}` : '');
L.push(`=== DSH 自检 (${tag})  ${result.at}  ${(Date.now() - t0) / 1000}s ===`);
if (result.kernel) L.push(`内核     cli=${result.kernel.cli}  exe=${result.kernel.exe}  electron=${result.kernel.electron}  一致=${result.kernel.match}`);
if (result.deps) L.push(`依赖     ${result.deps.count} deps / ${result.deps.bundles} bundles  掉出=[${result.deps.missingInBundles}]  多余=[${result.deps.extraInBundles}]`);
if (result.plugins) {
  L.push('插件：');
  for (const p of result.plugins) L.push(`  ${p.name.padEnd(46)} ${(p.version + '  ' + (p.update ?? '')).padEnd(18)} ${p.source.padEnd(9)} ${p.purpose}`);
  const cnt = result.plugins.reduce((a, p) => (a[p.update] = (a[p.update] || 0) + 1, a), {});
  const older = Object.keys(cnt).filter((k) => k.startsWith('旧')).reduce((s, k) => s + cnt[k], 0);
  L.push(`  版本：新 ${cnt['新'] || 0} / 待升级 ${older} / 自研或查不到 ${(cnt['自研'] || 0) + (cnt['无 tag'] || 0)}`);
}
if (result.plugDirs) {
  L.push('插件目录：');
  for (const [k, v] of Object.entries(result.plugDirs)) if (k !== 'total' && v) L.push(`  ${k.padEnd(18)} ${v.mb} MB / ${v.files} 文件`);
  L.push(`  合计 ${result.plugDirs.total.mb} MB / ${result.plugDirs.total.files} 文件`);
}
if (result.bili) L.push(`B站MCP   server=${result.bili.server}  cookie=${result.bili.cookieMtime} (${result.bili.cookieDaysAgo} 天前)  工具=${result.bili.mcp?.toolCount ?? '?'}  真调=${result.bili.mcp?.ok ? 'OK ' + (result.bili.mcp.sample || '') : 'FAIL ' + (result.bili.mcp?.error || result.bili.mcp?.sample || '')}`);
if (result.skills) {
  const sk = result.skills;
  const descSum = sk.user.reduce((a, s) => a + (s.descChars || 0), 0);
  L.push(`技能     user=${sk.user.map(s => `${s.name}(${s.descChars}c)`) .join(',')}`);
  L.push(`         插件自带 ${sk.pluginCount} 个：${Object.entries(sk.byPkg).map(([k, v]) => k.split('/').pop() + '(' + v.length + ')').join(' ')}`);
  L.push(`         目录估算 ${(sk.catalogChars || 0).toLocaleString()} 字符（name+description；自建 ${descSum.toLocaleString()}，disable-model-invocation 记 0）`);
  if (sk.dupNames?.length) L.push(`         ⚠ 同名技能 ${sk.dupNames.length} 个：${sk.dupNames.join('、')}——同名会静默覆盖，先扫到的赢`);
  const extra = sk.user.filter((s) => s.extraKeys?.length);
  if (extra.length) L.push(`         frontmatter 多余字段：${extra.map((s) => `${s.name}[${s.extraKeys.join('/')}]`).join(' ')}`);
}
if (result.workspace) {
  L.push(`工作区   ${result.workspace.total.mb} MB / ${result.workspace.total.files} 文件  ${result.workspace.root}`);
  const wsTop = Object.entries(result.workspace.children || {}).sort((a, b) => b[1].mb - a[1].mb).slice(0, 10);
  for (const [k, v] of wsTop) L.push(`  ${k.padEnd(16)} ${v.mb} MB / ${v.files}`);
}
if (result.home) {
  L.push(`HOME     ${result.home.total.mb} MB / ${result.home.total.files} 文件`);
  const top = Object.entries(result.home.children || {}).sort((a, b) => b[1].mb - a[1].mb).slice(0, 6);
  for (const [k, v] of top) L.push(`  ${k.padEnd(16)} ${v.mb} MB / ${v.files}`);
}
if (result.memory) {
  L.push(`记忆     active=${result.memory.active} all=${result.memory.all}  db=${result.memory.sizeMB}MB wal=${result.memory.walMB}MB` + (result.memory.dbPath ? `  库=${result.memory.dbPath}` : ''));
  for (const [k, v] of Object.entries(result.memory.byLevel || {})) L.push(`  ${k.padEnd(8)} ${v.active}/${v.all}`);
  if (result.memory.longest?.length) L.push(`  最长：` + result.memory.longest.map(x => `${x.level}:${x.id.slice(0, 9)}(${x.n}字)`).join(' '));
  const sk = result.memory.sink;
  if (sk) {
    if (sk.error) L.push(`  沉淀候选：读取失败 ${sk.error}`);
    else if (sk.skipped) L.push(`  沉淀候选：跳过（${sk.skipped}）`);
    else L.push(`  沉淀候选：${sk.total} 条 lesson/rules 像方法、未标去向（前 ${(sk.preview || []).length}：${(sk.preview || []).map((x) => `→${x.hint}`).join('、') || '无'}）`);
    const gp = sk.pluginGaps;
    if (gp && !gp.error && !gp.skipped) {
      if ((gp.total ?? 0) > 0) L.push(`  插件缺口：${gp.total} 个符号在自建插件源码里找不到（${gp.items.join('、')}）——可能是插件该补的能力`);
      else L.push('  插件缺口：无（近 7 天记忆提到的符号都在自建插件源码里）');
    } else if (gp && (gp.error || gp.skipped)) L.push(`  插件缺口：跳过（${gp.error || gp.skipped}）`);
  }
}
if (result.external) {
  L.push(`外部     QQ插件=${result.external.qqPlugin} 凭据=${result.external.qqCreds}  MinerU=${result.external.mineruPort18000}(${result.external.mineruHttp})  bsk=${result.external.bskDaemon}  GUI端口=${result.external.guiPorts}`);
  if (result.external.worktrees?.length) L.push(`  ⚠ 残留目录：${result.external.worktrees.join(', ')}`);
}
if (result.usage) {
  const u = result.usage;
  L.push(`使用     近 ${u.days} 天 · ${u.sessions} 个会话 / ${u.events} 事件`);
  if (u.gate) L.push(`  ⚠ ${u.gate}`);
  if (u.overhead) {
    const range = u.overhead.minChars !== u.overhead.chars
      ? `（会话间 ${u.overhead.minTools}–${u.overhead.tools} 个 / ${u.overhead.minChars.toLocaleString()}–${u.overhead.chars.toLocaleString()} 字符，取最全）`
      : '';
    L.push(`  常驻   工具 ${u.overhead.tools} 个 / ${u.overhead.chars.toLocaleString()} 字符${range} · 技能目录 ${(u.overhead.skillCatalogChars || 0).toLocaleString()} 字符 · AGENTS.md ${(u.agentsMdChars || 0).toLocaleString()} 字符`);
    if (u.overhead.mcpTools) {
      const pct = ((u.overhead.mcpChars / u.overhead.chars) * 100).toFixed(0);
      L.push(`  MCP    ${u.overhead.mcpTools} 个工具 / ${u.overhead.mcpChars.toLocaleString()} 字符（占工具面 ${pct}%；DSH 默认全量注入，超 20k 字符要拆）`);
    } else L.push('  MCP    未检出 mcp__ 前缀工具（0 个；有的 MCP 用具名而非 mcp__ 前缀，需人工核对）');
    const total = u.overhead.chars + (u.overhead.skillCatalogChars || 0) + (u.agentsMdChars || 0);
    const kTok = (total / 3.2 / 1000).toFixed(1);
    L.push(`  常驻合计 ≈ ${kTok}k token（按 3.2 字符/token 估）${total > 180000 ? '  ⚠ 超 180k 字符，把长内容挪进技能或样板' : ''}`);
  }
  const idle = u.idleSkills.map((n) => `${n}(${(u.descChars?.[n] || 0)}c)`);
  L.push(`  技能   ${Object.keys(u.skillsUsed).length} 个被触发${idle.length ? `；零触发（按字符降序，0 次不等于没用）：${idle.join(', ')}` : ''}`);
  if (Object.keys(u.ownerCalls).length) L.push(`  插件   ${Object.entries(u.ownerCalls).map(([k, v]) => `${k}(${v})`).join(' ')}`);
  if (u.idleOwners.length) L.push(`  零调用 ${u.idleOwners.join('、')}（映射表认得，30 天 0 次）`);
  if (u.toolTop.length) L.push(`  工具top ${u.toolTop.map(([k, v]) => `${k}(${v})`).join(' ')}`);
  L.push('  口径   hook 与后台类插件不写会话日志，属「仅静态盘点」；技能只认显式 skill 调用与 <skill_content>');
}
L.push('冒烟：');
for (const [k, v] of Object.entries(result.smoke.auto)) L.push(`  auto   ${k} = ${v}`);
L.push(`  manual ${result.smoke.manual.length} 项待对话侧执行（见 JSON smoke.manual）`);
if (ONLY) {
  L.push('差分     （--only 模式跳过）');
} else {
  L.push('差分：');
  if (result.diff.note) L.push(`  ${result.diff.note}`);
  else {
    L.push(`  基线 ${result.diff.baseline}`);
    for (const k of ['counts', 'changed', 'added', 'removed', 'vols', 'mem']) {
      const v = result.diff[k];
      if (!v?.length) continue;
      L.push(`  ${k}: ${v.join(' | ')}`);
    }
  }
}
L.push(`落档     ${outFile}`);
if (!ONLY) {
  const ov = result.memory?.over;
  L.push('');
  L.push('待人工对账（脚本不做，四件）：');
  L.push(`  1 记忆体检 —— 超长 >800 字 ${ov ? ov.n800 : '?'} 条 / >450 字 ${ov ? ov.n450 : '?'} 条；逐条读、判四类（错误 / 重复 / 已完结 / 超长）、当场改`);
  L.push('  2 技能引用 —— grep 旧包名 / 旧工具名 / 已卸插件名');
  L.push('  3 插件说明 —— 每个版本号从 package.json 核到');
  L.push('  4 脚本与流程图 —— 本轮行为变化是否要改脚本或文档');
}
console.log(L.join('\n'));
