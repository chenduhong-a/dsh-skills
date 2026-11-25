import { spawn, spawnSync } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';

const here = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
const biliMcp = process.env.BILI_MCP_DIR || 'C:/deepseek/tools/bili-mcp'; // 副本：原为 path.join(here,'..','bili-mcp')
const serverEntry = path.join(biliMcp, 'node_modules', 'bilibili-mcp-server', 'dist', 'index.js');
// ASR 与下载用的 Python：2026-11-24 卸掉 dsh-video-understand 后迁到 bili-vision 插件的独立 venv
// （faster-whisper 1.2.1 + ctranslate2 + av + yt-dlp 都在里面，510 MB，别重复建环境）。
const venvPy = process.env.BILI_VISION_PYTHON || path.join(process.env.USERPROFILE, '.dsh', 'bili-vision-venv', 'Scripts', 'python.exe');
// 数据目录默认放当前工作区（DSH 沙箱只保证 workspace 可写，避免每次提权）；
// 可用 BILI_READER_DATA 覆盖，落到脚本目录兜底时说明当前会话有完整权限。
let dataRoot = process.env.BILI_READER_DATA || path.join(process.cwd(), '.bili-transcript');
let cacheDir = path.join(dataRoot, 'cache');
let tmpDir = path.join(dataRoot, 'tmp');
try {
  fs.mkdirSync(cacheDir, { recursive: true });
  fs.mkdirSync(tmpDir, { recursive: true });
} catch {
  dataRoot = path.join(here, 'data');
  cacheDir = path.join(dataRoot, 'cache');
  tmpDir = path.join(dataRoot, 'tmp');
  fs.mkdirSync(cacheDir, { recursive: true });
  fs.mkdirSync(tmpDir, { recursive: true });
}
const legacyCacheDir = path.join(here, 'cache');

const raw = process.argv[2] || '';
const bvid = (raw.match(/BV[0-9A-Za-z]{10}/) || [])[0];
const opusId = (raw.match(/\/opus\/(\d+)/) || [])[1];
if (!bvid && !opusId) { console.error('usage: node transcript.mjs <BV号/视频URL/opus 链接>'); process.exit(2); }
const cachePath = bvid ? path.join(cacheDir, bvid + '.txt') : '';
const t0 = Date.now();

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function extractInitialState(html) {
  const i = html.indexOf('window.__INITIAL_STATE__');
  if (i < 0) throw new Error('页面没有 __INITIAL_STATE__（可能被风控/改版）');
  const start = html.indexOf('{', i);
  let depth = 0, end = -1, inStr = false, esc = false;
  for (let k = start; k < html.length; k++) {
    const ch = html[k];
    if (inStr) { if (esc) esc = false; else if (ch === '\\') esc = true; else if (ch === '"') inStr = false; continue; }
    if (ch === '"') { inStr = true; continue; }
    if (ch === '{') depth++;
    else if (ch === '}') { depth--; if (depth === 0) { end = k + 1; break; } }
  }
  return JSON.parse(html.slice(start, end));
}

// opus 图文：PC UA 抓页面，正文在 detail.modules 的 MODULE_TYPE_CONTENT
// paragraphs[].text.nodes[].word.words（嵌套一层），无需登录。
async function readOpus(id) {
  const url = `https://www.bilibili.com/opus/${id}`;
  const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36';
  const res = await fetch(url, { headers: { 'User-Agent': UA, Referer: 'https://www.bilibili.com/' } });
  const html = await res.text();
  const state = extractInitialState(html);
  const modules = state.detail?.modules || [];
  const title = modules.find((m) => m.module_type === 'MODULE_TYPE_TITLE')?.module_title?.text || '';
  const author = modules.find((m) => m.module_type === 'MODULE_TYPE_AUTHOR')?.module_author?.name || '';
  const content = modules.find((m) => m.module_type === 'MODULE_TYPE_CONTENT');
  const paras = content?.module_content?.paragraphs || [];
  const lines = [];
  for (const p of paras) {
    const nodes = p?.text?.nodes || [];
    const text = nodes.map((n) => n.words || n.word?.words || n.rich?.orig_text || n.rich?.text || '').join('');
    if (text.trim()) lines.push(text.trim());
  }
  const pics = paras.filter((p) => p?.pic).length;
  const outPath = path.join(dataRoot, 'opus', id + '.txt');
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, lines.join('\n'), 'utf8');
  return {
    kind: 'opus',
    id,
    title,
    author,
    paragraphs: lines.length,
    chars: lines.join('\n').length,
    pics,
    source: 'opus',
    out: outPath,
    seconds: Math.round((Date.now() - t0) / 1000),
    head: lines.slice(0, 4),
  };
}

function readCache() {
  if (fs.existsSync(cachePath)) return fs.readFileSync(cachePath, 'utf8');
  // 旧版本把缓存写在脚本目录；沙箱会话读得到、写不进去，迁移一份到当前数据目录。
  const legacy = path.join(legacyCacheDir, bvid + '.txt');
  if (fs.existsSync(legacy)) {
    const text = fs.readFileSync(legacy, 'utf8');
    try { fs.writeFileSync(cachePath, text, 'utf8'); } catch { /* read-only fallback */ }
    return text;
  }
  return null;
}

// MCP over regular files instead of pipes: the Windows sandbox rejects
// stdio 'pipe' for child processes (spawn EPERM), so feed stdin from a file
// and read stdout from a file.
async function subtitleViaMcp() {
  const inP = path.join(tmpDir, `mcp-${bvid}-${process.pid}.in.jsonl`);
  const outP = path.join(tmpDir, `mcp-${bvid}-${process.pid}.out.jsonl`);
  const reqs = [
    { jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'bili-transcript', version: '0.1' } } },
    { jsonrpc: '2.0', method: 'notifications/initialized' },
    { jsonrpc: '2.0', id: 2, method: 'tools/call', params: { name: 'bilibili_video_subtitle', arguments: { videoId: bvid } } },
  ];
  fs.writeFileSync(inP, reqs.map((r) => JSON.stringify(r)).join('\n') + '\n');
  const fdIn = fs.openSync(inP, 'r');
  const fdOut = fs.openSync(outP, 'w');
  const child = spawn(process.execPath, [serverEntry], {
    stdio: [fdIn, fdOut, 'ignore'],
    env: { ...process.env, BILIBILI_COOKIE_FILE: path.join(biliMcp, 'cookie.json') },
  });
  fs.closeSync(fdIn);
  fs.closeSync(fdOut);
  const deadline = Date.now() + 30000;
  let response = null;
  while (Date.now() < deadline) {
    await sleep(150);
    let lines = [];
    try { lines = fs.readFileSync(outP, 'utf8').split('\n').filter(Boolean); } catch { break; }
    for (const line of lines) {
      try {
        const m = JSON.parse(line);
        if (m.id === 2) response = m;
      } catch { /* ignore logs */ }
    }
    if (response) break;
  }
  try { child.kill(); } catch { /* ignore */ }
  try { fs.rmSync(inP, { force: true }); fs.rmSync(outP, { force: true }); } catch { /* ignore */ }
  const text = response?.result?.content?.find((c) => c.type === 'text')?.text || '';
  return text.includes('📝 字幕') ? text : null;
}

// spawnSync with stdout/stderr redirected to files (no pipes under sandbox).
function runQuiet(cmd, args, env, errPath, what) {
  const efd = fs.openSync(errPath, 'w');
  const r = spawnSync(cmd, args, { stdio: ['ignore', 'ignore', efd], env });
  fs.closeSync(efd);
  if (r.status !== 0) {
    let err = '';
    try { err = fs.readFileSync(errPath, 'utf8').slice(-300); } catch { /* ignore */ }
    throw new Error(`${what} failed: ${err}`);
  }
}

function asrFallback() {
  const asrPy = path.join(here, 'asr.py');
  if (!fs.existsSync(venvPy)) throw new Error(`找不到 ASR 用的 python：${venvPy}（bili-vision-venv 不在了，需重建或改 BILI_VISION_PYTHON）`);
  if (!fs.existsSync(asrPy)) throw new Error(`找不到 ${asrPy}（ASR 脚本随技能走，别从插件目录找）`);
  const env = {
    ...process.env,
    PATH: 'C:\\deepseek\\tools\\bin;' + (process.env.PATH || ''),
    HF_ENDPOINT: 'https://hf-mirror.com',
    HF_HUB_DISABLE_XET: '1',
  };
  const base = path.join(tmpDir, bvid);
  for (const f of fs.readdirSync(tmpDir)) {
    if (f.startsWith(bvid)) fs.rmSync(path.join(tmpDir, f), { force: true });
  }
  runQuiet(venvPy, ['-m', 'yt_dlp', '-f', 'bv*[height<=360]+ba/b[height<=360]/worst', '--no-playlist', '-o', base + '.%(ext)s', `https://www.bilibili.com/video/${bvid}/`], env, path.join(tmpDir, bvid + '.ytdlp.err'), 'yt-dlp');
  const video = fs.readdirSync(tmpDir).find((f) => f.startsWith(bvid + '.') && !f.endsWith('.jsonl') && !f.endsWith('.wav') && !f.endsWith('.err'));
  if (!video) throw new Error('no video downloaded');
  const jsonl = path.join(tmpDir, bvid + '.jsonl');
  const device = process.env.FORCE_CPU === '1' ? 'cpu' : 'auto';
  runQuiet(venvPy, [asrPy, '--video', path.join(tmpDir, video), '--out', jsonl, '--model', 'base', '--lang', 'zh', '--device', device], env, path.join(tmpDir, bvid + '.asr.err'), 'asr');
  const rows = fs.readFileSync(jsonl, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l));
  const lines = rows.map((r) => {
    const s = Math.floor(r.start);
    return `[${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}] ${r.text}`;
  });
  // 转写成功后清理下载的视频/音频/中间文件，只保留 cache/ 下的转写文本；
  // 失败时异常抛出，中间文件保留便于排查。
  for (const f of fs.readdirSync(tmpDir)) {
    if (f.startsWith(bvid)) fs.rmSync(path.join(tmpDir, f), { force: true });
  }
  return `📝 字幕 (ASR base / ${device}):\n` + lines.join('\n');
}

try {
  if (opusId && !bvid) {
    const opus = await readOpus(opusId);
    console.log(JSON.stringify(opus, null, 2));
    process.exit(0);
  }
  let text = readCache();
  let source = 'cache';
  if (!text) {
    if (process.env.FORCE_ASR === '1') {
      text = asrFallback();
      source = 'ASR base (forced)';
    } else {
      text = await subtitleViaMcp();
      source = 'B站字幕';
      if (!text) { text = asrFallback(); source = 'ASR base'; }
    }
    fs.writeFileSync(cachePath, text, 'utf8');
  }
  const lines = text.split('\n').filter(Boolean);
  console.log(JSON.stringify({
    bvid,
    source,
    seconds: Math.round((Date.now() - t0) / 1000),
    lines: lines.length,
    cache: cachePath,
    head: lines.slice(0, 6),
  }, null, 2));
} catch (e) {
  console.error('ERROR ' + (e?.message || e));
  process.exit(1);
}
