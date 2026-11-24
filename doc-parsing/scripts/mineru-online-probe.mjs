#!/usr/bin/env node
/**
 * MinerU 官方在线 API 探针（mineru.net /api/v4）
 *
 * 为什么先写探针再改插件：官方接口是「上传 → 提交 → 轮询 → 下 zip」四段异步流程，
 * 请求体字段与本地 /file_parse 完全不同。先用最小脚本把字段确认真，再并进 dsh-doc-parser，
 * 免得猜错字段后在插件里返工。
 *
 * 用法：
 *   node mineru-online-probe.mjs <pdf路径> [--pages 1-3] [--model vlm] [--keep]
 *
 * token 来源（二选一，不写进命令行）：
 *   1) 环境变量 MINERU_API_TOKEN
 *   2) 文件 C:\deepseek\tools\.mineru-token（单行，无引号）
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';

const API_BASE = (process.env.MINERU_API_BASE || 'https://mineru.net').replace(/\/+$/, '');
const TOKEN_FILE = process.env.MINERU_TOKEN_FILE || 'C:\\deepseek\\tools\\.mineru-token';
const POLL_MS = Number(process.env.MINERU_POLL_MS || 5000);
const MAX_WAIT_MS = Number(process.env.MINERU_MAX_WAIT_MS || 45 * 60 * 1000);

function log(...a) {
  process.stderr.write(`[${new Date().toISOString().slice(11, 19)}] ${a.join(' ')}\n`);
}

function token() {
  const env = String(process.env.MINERU_API_TOKEN || '').trim();
  if (env) return env;
  try {
    const t = fs.readFileSync(TOKEN_FILE, 'utf8').trim();
    if (t) return t;
  } catch {
    /* fallthrough */
  }
  throw new Error(
    `token 没找到。把它写进 ${TOKEN_FILE}（单行、不要引号），或设环境变量 MINERU_API_TOKEN。`,
  );
}

async function apiCall(pathname, { method = 'GET', body, timeoutMs = 60000 } = {}) {
  const headers = { Authorization: `Bearer ${token()}` };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const res = await fetch(API_BASE + pathname, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(timeoutMs),
  });
  const text = await res.text();
  let json = null;
  try {
    json = JSON.parse(text);
  } catch {
    /* 非 JSON 直接报原始 */
  }
  if (!res.ok) throw new Error(`${method} ${pathname} → HTTP ${res.status}: ${text.slice(0, 400)}`);
  if (!json) throw new Error(`${method} ${pathname} → 非 JSON 响应: ${text.slice(0, 300)}`);
  const code = json.code;
  if (code !== undefined && code !== 0 && code !== 200) {
    throw new Error(`${method} ${pathname} → code=${code} msg=${json.msg || ''}`);
  }
  return json.data ?? json;
}

function parseArgs(argv) {
  const out = { file: '', pages: '', model: 'vlm', keep: false };
  const rest = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--pages') out.pages = argv[++i] || '';
    else if (a === '--model') out.model = argv[++i] || 'vlm';
    else if (a === '--keep') out.keep = true;
    else if (a.startsWith('--')) throw new Error(`未知参数 ${a}`);
    else rest.push(a);
  }
  out.file = rest[0] || '';
  if (!out.file) throw new Error('用法：node mineru-online-probe.mjs <pdf路径> [--pages 1-3] [--model vlm] [--keep]');
  return out;
}

/** 解析 "1-3,5" → [1,2,3,5] */
function parsePages(spec, total) {
  if (!spec) return null;
  const set = new Set();
  for (const part of String(spec).split(',')) {
    const p = part.trim();
    if (!p) continue;
    const m = /^(\d+)(?:-(\d+))?$/.exec(p);
    if (!m) throw new Error(`页范围写法不对: ${p}`);
    const a = Number(m[1]);
    const b = m[2] ? Number(m[2]) : a;
    for (let n = Math.min(a, b); n <= Math.max(a, b); n++) {
      if (n >= 1 && (!total || n <= total)) set.add(n);
    }
  }
  return [...set].sort((x, y) => x - y);
}

/** PUT 上传原始字节到预签名 URL（这不带 token，URL 自带签名） */
async function uploadFile(fileUrl, buf, timeoutMs = 600000) {
  // ⚠️ 不要带 Content-Type：OSS 预签名 URL 的签名把这些 header 也算了进去，
  // 多一个 application/octet-stream 就 SignatureDoesNotMatch（2026-11-13 实测 403）。
  const res = await fetch(fileUrl, {
    method: 'PUT',
    body: buf,
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!res.ok) {
    const t = await res.text().catch(() => '');
    throw new Error(`上传失败 HTTP ${res.status}: ${t.slice(0, 300)}`);
  }
}

async function pollBatch(batchId) {
  const t0 = Date.now();
  let last = '';
  for (;;) {
    const data = await apiCall(`/api/v4/extract-results/batch/${encodeURIComponent(batchId)}`);
    const list = Array.isArray(data.extract_result) ? data.extract_result : [];
    const one = list[0] || {};
    const state = one.state || 'unknown';
    const pr = one.extract_progress || {};
    const prog =
      pr.total_pages !== undefined ? ` ${pr.extracted_pages ?? 0}/${pr.total_pages} 页` : '';
    const line = `${state}${prog}`;
    if (line !== last) {
      log('轮询:', line);
      last = line;
    }
    if (state === 'done') return one;
    if (state === 'failed') throw new Error(`解析失败: ${one.err_msg || '未知原因'}`);
    if (Date.now() - t0 > MAX_WAIT_MS) throw new Error(`等待超时（>${MAX_WAIT_MS / 60000} 分钟）`);
    await new Promise((r) => setTimeout(r, POLL_MS));
  }
}

async function downloadZip(url, dir) {
  log('下载 zip …');
  const res = await fetch(url, { signal: AbortSignal.timeout(600000) });
  if (!res.ok) throw new Error(`下载失败 HTTP ${res.status}`);
  const buf = Buffer.from(await res.arrayBuffer());
  const zip = path.join(dir, 'result.zip');
  fs.writeFileSync(zip, buf);
  log(`zip ${(buf.length / 1024 / 1024).toFixed(2)} MB`);
  const out = path.join(dir, 'out');
  fs.mkdirSync(out, { recursive: true });
  // Windows 10+ 自带 tar（bsdtar）能解 zip；比在 node 里手写 central directory 解析稳。
  const r = spawnSync('tar', ['-xf', zip, '-C', out], { encoding: 'utf8' });
  if (r.status !== 0) throw new Error(`解压失败: ${r.stderr || r.status}`);
  return out;
}

function findContentList(dir) {
  const stack = [dir];
  while (stack.length) {
    const cur = stack.pop();
    let entries = [];
    try {
      entries = fs.readdirSync(cur, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const e of entries) {
      const abs = path.join(cur, e.name);
      if (e.isDirectory()) stack.push(abs);
      else if (/content_list\.json$/i.test(e.name)) return abs;
    }
  }
  return '';
}

function pageTexts(items) {
  const byPage = new Map();
  for (const it of items) {
    const idx = Number(it.page_idx);
    if (!Number.isFinite(idx)) continue;
    const p = idx + 1; // API 的 page_idx 是整本 0-based
    let chunk = '';
    const tp = it.type || 'text';
    if (tp === 'equation') {
      const body = String(it.latex || it.text || '').trim();
      chunk = body ? (body.startsWith('$$') ? body : `$$\n${body}\n$$`) : '';
    } else if (tp === 'table') {
      chunk = String(it.table_body || it.text || '');
    } else if (tp === 'image' || tp === 'figure') {
      const cap = Array.isArray(it.image_caption) ? it.image_caption.join(' ') : String(it.image_caption || '');
      chunk = `[figure${cap ? ': ' + cap : ''}${it.img_path ? ` — ${it.img_path}` : ''}]`;
    } else {
      chunk = String(it.text || '');
    }
    if (!chunk) continue;
    if (!byPage.has(p)) byPage.set(p, []);
    byPage.get(p).push(chunk);
  }
  return byPage;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const abs = path.resolve(args.file);
  const st = fs.statSync(abs);
  log(`文件 ${path.basename(abs)} ${(st.size / 1024 / 1024).toFixed(2)} MB · model=${args.model}`);
  const buf = fs.readFileSync(abs);

  log('① 申请上传链接 …');
  const up = await apiCall('/api/v4/file-urls/batch', {
    method: 'POST',
    body: {
      files: [{ name: path.basename(abs), data_id: path.basename(abs) }],
      model_version: args.model,
    },
  });
  const batchId = up.batch_id;
  const fileUrl = (up.file_urls && up.file_urls[0]) || (Array.isArray(up.files) ? up.files[0]?.file_url : '');
  if (!batchId || !fileUrl) throw new Error(`上传链接响应不符合预期: ${JSON.stringify(up).slice(0, 400)}`);
  log(`   batch_id=${batchId}`);

  log('② 上传 PDF …');
  await uploadFile(fileUrl, buf);
  log('   已上传');

  log('③ 轮询解析状态 …');
  const done = await pollBatch(batchId);
  log(`   完成: ${done.file_name || ''} ${done.full_zip_url || ''}`);

  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'mineru-online-'));
  const outDir = await downloadZip(done.full_zip_url, tmp);

  const clPath = findContentList(outDir);
  if (!clPath) {
    log('zip 里没找到 content_list.json，列出文件:');
    const walk = (d) => {
      for (const e of fs.readdirSync(d, { withFileTypes: true })) {
        const abs2 = path.join(d, e.name);
        if (e.isDirectory()) walk(abs2);
        else log('   ', path.relative(outDir, abs2));
      }
    };
    walk(outDir);
    throw new Error('没有 content_list.json，无法按页重建文本');
  }
  const items = JSON.parse(fs.readFileSync(clPath, 'utf8'));
  log(`content_list: ${items.length} 个块 · ${path.relative(outDir, clPath)}`);

  const byPage = pageTexts(items);
  const total = Math.max(...byPage.keys(), 0);
  const want = parsePages(args.pages, total);
  const pages = want || [...byPage.keys()].sort((a, b) => a - b);
  log(`共 ${total} 页，打印 ${pages.length} 页`);
  for (const p of pages.slice(0, Number(process.env.MINERU_PROBE_PAGES || 3))) {
    const text = (byPage.get(p) || []).join('\n\n');
    console.log(`\n===== page ${p} (${text.length} chars) =====`);
    console.log(text.slice(0, 1500));
  }

  if (args.keep) log(`产物保留在 ${outDir}`);
  else fs.rmSync(tmp, { recursive: true, force: true });
}

main().catch((e) => {
  console.error('失败:', e.message);
  process.exitCode = 1;
});
