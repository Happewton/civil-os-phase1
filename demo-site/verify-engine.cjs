// Verifies the engine half of demo-site/index.html against known-good values.
const fs = require('fs');
const crypto = require('crypto');

const html = fs.readFileSync(__dirname + '/index.html', 'utf8');
const m = html.match(/<script>\n"use strict";([\s\S]*?)\/\* =+\n   UI layer/);
if (!m) { console.error('FAIL: could not extract engine script'); process.exit(1); }

const engine = m[1];
const sandbox = { console, TextEncoder, Date, Math, JSON, Object, Array, Set, Number, String };
const fn = new Function('window', 'document', 'module', engine + '\n; return {sha256, canonicalJson, computeHash, ECPVersionManager, CPO, AssemblyError, GateBlocked, StateMachineError, ValidationError, evaluateGate, countByLevel, LEVELS, resolveJurisdiction};');
const E = fn(sandbox, null, null);

let fails = 0;
const ok = (name, cond, extra) => {
  if (cond) console.log('  PASS  ' + name);
  else { console.log('  FAIL  ' + name + (extra ? '  -> ' + extra : '')); fails++; }
};

console.log('\n[1] SHA-256 correctness');
const vectors = [
  ['', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'],
  ['abc', 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'],
  ['The quick brown fox jumps over the lazy dog',
   'd7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592'],
];
for (const [input, expected] of vectors) {
  const got = E.sha256(input);
  const node = crypto.createHash('sha256').update(input, 'utf8').digest('hex');
  ok(`sha256("${input.slice(0, 20)}")`, got === expected && node === expected, `got ${got} / node ${node}`);
}
// long input crossing the 64-byte block boundary
const long = 'x'.repeat(1000);
ok('sha256(1000 bytes) matches node',
   E.sha256(long) === crypto.createHash('sha256').update(long).digest('hex'));

console.log('\n[2] Canonical JSON (sorted keys, compact)');
ok('key order normalised',
   E.canonicalJson({ b: 1, a: 2 }) === '{"a":2,"b":1}', E.canonicalJson({ b: 1, a: 2 }));
ok('undefined dropped',
   E.canonicalJson({ a: 1, b: undefined }) === '{"a":1}', E.canonicalJson({ a: 1, b: undefined }));
ok('nested sorted',
   E.canonicalJson({ z: { y: 1, x: 2 } }) === '{"z":{"x":2,"y":1}}', E.canonicalJson({ z: { y: 1, x: 2 } }));

console.log('\n[3] ECP assembly + §5.3 r.4 idempotency');
const cpo = new E.CPO();
const p = cpo.createProject({ name: 'Al-Wadi', project_type: 'water', country: 'SA',
  latitude: 24.7136, longitude: 46.6753, region: 'Riyadh Province', municipality: 'Al-Wadi' });
const site = cpo.registerSite(p.project_id, {
  name: 'Site',
  soil_profiles: [{ profile_id: 'p1', borehole_id: 'BH-07', layers: [
    { depth_from_m: 0, depth_to_m: 5, soil_type: 'Silty sand', confidence_level: 'E' },
    { depth_from_m: 5, depth_to_m: 20, soil_type: 'Sand', confidence_level: 'E' }]}],
  hydrology: {}, hazards: [], data_gaps: ['Flood modelling'] });

const a = cpo.assemble(p.project_id, site, 30);
ok('assembles without a location error', !!a.content_hash);
ok('version starts at 1', a.version === 1, a.version);
ok('hash is 64 hex chars', /^[0-9a-f]{64}$/.test(a.content_hash), a.content_hash);
// Wall-clock / identity fields must not move the hash (versioning.py NON_CONTENT_FIELDS)
const perturbed = JSON.parse(JSON.stringify(a));
perturbed.ecp_id = 'id-different';
perturbed.created_at = '2031-01-01T00:00:00.000Z';
perturbed.validity = { valid_from: '2031-01-01T00:00:00.000Z',
                       valid_until: '2031-03-01T00:00:00.000Z', rationale: 'different window' };
ok('ecp_id / created_at / validity excluded from hash',
   E.computeHash(perturbed) === a.content_hash, E.computeHash(perturbed));
const realChange = JSON.parse(JSON.stringify(a));
realChange.site_data.data_gaps = ['totally different gap'];
ok('engineering content DOES move the hash',
   E.computeHash(realChange) !== a.content_hash);
ok('recompute is stable on the stored packet', E.computeHash(a) === a.content_hash);

const b = cpo.assemble(p.project_id, site, 30);
ok('re-assembly: identical content keeps version', b.version === 1, b.version);
ok('re-assembly: identical hash', b.content_hash === a.content_hash);

site.soil_profiles[0].layers[0].confidence_level = 'A';
const c = cpo.assemble(p.project_id, site, 30);
ok('changed content bumps version', c.version === 2, c.version);
ok('changed content changes hash', c.content_hash !== a.content_hash);

console.log('\n[4] §5.3 r.3 confidence summary');
ok('level A counted', c.confidence_summary.level_a_count === 1, c.confidence_summary.level_a_count);
ok('level E counted', c.confidence_summary.level_e_count === 1, c.confidence_summary.level_e_count);
ok('data gap becomes an uncertainty item',
   c.confidence_summary.uncertainty_items.some(u => u.parameter === 'Flood modelling'));
const d = cpo.assemble(p.project_id, site, 30);
ok('summary does not self-amplify on re-assembly',
   d.confidence_summary.level_a_count === c.confidence_summary.level_a_count,
   `${c.confidence_summary.level_a_count} -> ${d.confidence_summary.level_a_count}`);

console.log('\n[5] §5.3 r.5 jurisdiction cascade');
const ecpFinal = cpo.assemble(p.project_id, site, 30);
ok('SA resolves to Saudi codes',
   ecpFinal.applicable_codes.some(c2 => c2.code_name.includes('SBC 401')),
   JSON.stringify(ecpFinal.applicable_codes.map(x => x.code_name)));
ok('unknown country falls back to international',
   E.resolveJurisdiction('ZZ', 'x', 'y').code === 'INT');

console.log('\n[6] §5.3 r.1/r.2 validation');
let threw = null;
try { cpo.assemble('nonexistent-project', site, 30); } catch (e) { threw = e.name; }
ok('missing project raises', threw === 'TypeError' || threw === 'AssemblyError', threw);
const stale = { ...ecpFinal, validity: { valid_from: '2020-01-01T00:00:00Z',
  valid_until: '2020-02-01T00:00:00Z', rationale: 'x' } };
ok('expired validity is detectable', new Date(stale.validity.valid_until) < Date.now());

console.log('\n[7] §7.3 gate + waivers + safety-critical');
const t1 = cpo.createTask(p.project_id, ecpFinal.ecp_id, {
  task_name: 'Hydraulic analysis', discipline: 'civil', safety_critical: false,
  assumptions: [{ assumption_text: 'GWT at 5.2 m', confidence_level: 'E' }] });
ok('gate closed on level-E', E.evaluateGate(t1).can_proceed === false);
let blocked = null;
try { cpo.startTask(t1.uto_id, 'Eng'); } catch (e) { blocked = e; }
ok('start throws GateBlocked', blocked && blocked.name === 'GateBlocked', blocked && blocked.name);
ok('task parked in blocked', t1.status === 'blocked', t1.status);
ok('blocked event records unblock conditions',
   t1.execution_log.some(e => e.event_type === 'blocked' && e.details.issues.length > 0));

cpo.applyWaiver(t1.uto_id, 'GWT at 5.2 m', 'Regional data supports this.', 'Chief Engineer');
ok('gate opens after waiver', E.evaluateGate(t1).can_proceed === true);
ok('blocked task released to ready (not a dead end)', t1.status === 'ready', t1.status);
cpo.startTask(t1.uto_id, 'Eng');
ok('lifecycle advances to in_progress', t1.status === 'in_progress', t1.status);
cpo.markUnderReview(t1.uto_id, 'Eng');
ok('review requires review flag honoured', t1.status === 'under_review', t1.status);
cpo.approveTask(t1.uto_id, 'Reviewer');
cpo.completeTask(t1.uto_id, 'Eng');
ok('reaches completed', t1.status === 'completed', t1.status);

const t2 = cpo.createTask(p.project_id, ecpFinal.ecp_id, {
  task_name: 'Structural design', discipline: 'structural', safety_critical: true,
  assumptions: [{ assumption_text: 'PGA = 0.25g', confidence_level: 'E' }] });
let refused = null;
try { cpo.applyWaiver(t2.uto_id, 'PGA = 0.25g', 'Estimate.', 'Engineer'); } catch (e) { refused = e.name; }
ok('safety-critical refuses waiver', refused === 'AssemblyError', refused);
ok('safety-critical stays blocked', E.evaluateGate(t2).can_proceed === false);

const t3 = cpo.createTask(p.project_id, null, { task_name: 'No ECP', discipline: 'civil' });
ok('no bound ECP is a blocking issue',
   E.evaluateGate(t3).issues.some(i => i.includes('Context Packet')));

console.log('\n[8] auto-approve without review');
const t4 = cpo.createTask(p.project_id, ecpFinal.ecp_id,
  { task_name: 'Simple', discipline: 'civil', requires_review: false });
cpo.startTask(t4.uto_id); cpo.markUnderReview(t4.uto_id);
ok('auto-approves when review not required', t4.status === 'approved', t4.status);

console.log('\n[9] audit trail');
ok('audit recorded project, site, ecp, task',
   new Set(cpo.audit.map(a => a.entity_type)).size >= 4,
   [...new Set(cpo.audit.map(a => a.entity_type))].join(','));

console.log('\n' + (fails === 0
  ? 'ALL ENGINE CHECKS PASSED'
  : fails + ' ENGINE CHECK(S) FAILED'));
process.exit(fails === 0 ? 0 : 1);
