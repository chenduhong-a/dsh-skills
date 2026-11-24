// meow-mind 索引重建：memory_fts（分词口径）+ memory_vectors（bge-base-zh-v1.5）
//
// 用法（用 runtime 的 node，别用系统 node —— 要 node:sqlite）：
//   $env:ELECTRON_RUN_AS_NODE='1'
//   & $node rebuild-index.mjs                                  # 重建全局库
//   & $node rebuild-index.mjs <工作区>\.dsh-mind\memory.db      # 重建指定库
//   & $node rebuild-index.mjs <库> <meow-mind 目录>             # 显式指定插件目录
//
// 判据：末行 MUST 是 PASS（active = fts = vectors，且没有异模型向量），
// 再挑一个只在重建后才搬进库的词跑 memory_search 验证能命中。
//
// 两个必须照抄的口径（抄错就静默搜不到）：
//   1) body 必须走 meow-mind 的 buildBody（中文 2-gram 滑动、单字保留、keywords 拼两遍加权）
//   2) vectors 必须先整表清空再写；只 upsert 会把已归档条目的旧向量留成孤儿，
//      自检条数永远对不上（2026-11-22 实测全局多 3 条、工作区多 658 条）
import { DatabaseSync } from 'node:sqlite';
import { pathToFileURL } from 'node:url';
import { existsSync } from 'node:fs';

const argDb = process.argv[2];
const argRoot = process.argv[3];
const HOME = process.env.DSH_HOME || `${process.env.USERPROFILE}\\.dsh`;

const TARGET = argDb || 'C:\\deepseek\\.dsh-mind-global\\memory.db';
const PLUGIN = argRoot || `${HOME}\\profiles\\desktop\\node_modules\\meow-mind`;

if (!existsSync(`${PLUGIN}\\src\\embed.mjs`)) {
  console.error(`!! 找不到 meow-mind：${PLUGIN}\n   第三个参数显式传插件目录，或先确认插件已安装。`);
  process.exit(2);
}
const { createEmbedder } = await import(pathToFileURL(`${PLUGIN}/src/embed.mjs`).href);
const { buildBody } = await import(pathToFileURL(`${PLUGIN}/src/vocab.mjs`).href);

const LEVELS = ['soul', 'user', 'project', 'fact', 'lesson', 'topic', 'rules', 'todo'];
const VEC_MODEL = 'bge-base-zh-v1.5';
const BATCH = 8;
const cfg = { embedding: { enabled: true, model: 'Xenova/bge-base-zh-v1.5', dtype: 'q8', localPath: '', allowRemote: false } };

const db = new DatabaseSync(TARGET);
const now = new Date().toISOString().replace('Z', '');
console.log('库:', TARGET);
console.log('插件:', PLUGIN);

// 1) 收集活跃条目
const rows = [];
for (const lv of LEVELS) {
  const has = db.prepare(`select name from sqlite_master where type='table' and name=?`).get(lv);
  if (!has) continue;
  for (const r of db.prepare(`select id, title, content, keywords from ${lv} where status='memory'`).all()) {
    rows.push({ ...r, level: lv });
  }
}
console.log('活跃条目:', rows.length);
if (!rows.length) { console.log('没有活跃条目，退出'); db.close(); process.exit(0); }

// 2) 重建 memory_fts（整表重写，不做增量）
db.exec('delete from memory_fts');
const insFts = db.prepare('insert into memory_fts (memory_id, level, body) values (?,?,?)');
for (const r of rows) insFts.run(r.id, r.level, buildBody(r.title ?? '', r.content ?? '', r.keywords ?? ''));
console.log('memory_fts 重建:', rows.length);

// 3) 重建 memory_vectors（先清表，避免孤儿）
db.exec('delete from memory_vectors');
const em = await createEmbedder(cfg, { info: m => console.log(m) });
const insVec = db.prepare('insert or replace into memory_vectors (memory_id, level, dim, vec, model, updated_at) values (?,?,?,?,?,?)');
let done = 0;
for (let i = 0; i < rows.length; i += BATCH) {
  const chunk = rows.slice(i, i + BATCH);
  const texts = chunk.map(r => `${r.title ?? ''}\n${r.content ?? ''}\n${r.keywords ?? ''}`.trim().slice(0, 1000));
  const vecs = await em.embedBatch(texts);
  for (let k = 0; k < chunk.length; k++) {
    const f = vecs[k];
    insVec.run(chunk[k].id, chunk[k].level, f.length, Buffer.from(f.buffer, f.byteOffset, f.byteLength), VEC_MODEL, now);
    done++;
  }
  process.stdout.write(`\r  向量 ${done}/${rows.length}`);
}
console.log('\nmemory_vectors 重建:', done);

// 4) 自检
const c1 = db.prepare('select count(*) c from memory_fts').get().c;
const c2 = db.prepare('select count(*) c from memory_vectors').get().c;
const c3 = db.prepare('select count(*) c from memory_vectors where model<>?').get(VEC_MODEL).c;
console.log(`自检: active=${rows.length} fts=${c1} vectors=${c2} 异模型=${c3}`);
console.log(c1 === rows.length && c2 === rows.length && c3 === 0 ? 'PASS' : 'FAIL（条数不一致）');
db.close();
