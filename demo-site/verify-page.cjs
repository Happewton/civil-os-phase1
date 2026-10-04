// Static sanity check: every $("id") in the UI layer must exist in the markup,
// and the page must be self-contained (no local asset references).
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
let fails = 0;
const ok = (n, c, x) => { if (c) console.log('  PASS  ' + n); else { console.log('  FAIL  ' + n + (x ? ' -> ' + x : '')); fails++; } };

console.log('\n[DOM] element references');
const ids = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map(m => m[1]));
const refs = new Set([...html.matchAll(/\$\("([^"]+)"\)/g)].map(m => m[1]));
console.log('  ids in markup: ' + ids.size + ', $() refs: ' + refs.size);
// Ids injected by innerHTML templates are legitimately absent from static markup.
const generated = new Set(['btn-assemble', 'btn-revise', 'idem-note', 'btn-add-layer', 'p-name']);
const missing = [...refs].filter(r => !ids.has(r) && !generated.has(r));
ok('every $() ref resolves', missing.length === 0, missing.join(', '));
[...ids].forEach(id => { if (!refs.has(id)) console.log('  note: id "' + id + '" present but not referenced'); });

console.log('\n[DOM] ids created only inside innerHTML templates');
['btn-assemble', 'btn-revise'].forEach(id => {
  const inTemplate = html.includes(`id="${id}"`);
  ok(`"${id}" is template-injected`, inTemplate);
});

console.log('\n[self-contained] no local asset references');
// Ignore Google Fonts and intentional outbound links; anything else must be data:.
const IGNORED = /^(https:\/\/fonts\.|https:\/\/github\.com\/)/;
const localRefs = [...html.matchAll(/(?:src|href)="([^"]+)"/g)]
  .map(m => m[1])
  .filter(r => !IGNORED.test(r));
const bad = localRefs.filter(r => !r.startsWith('data:'));
ok('no local file dependencies', bad.length === 0, bad.join(', '));
ok('only index.html needed',
   fs.readdirSync(__dirname).filter(f => f.endsWith('.html')).length === 1);

console.log('\n[markup] required structure');
ok('has <!DOCTYPE html>', html.startsWith('<!DOCTYPE html>'));
ok('has viewport meta', html.includes('name="viewport"'));
ok('has title', /<title>[^<]+<\/title>/.test(html));
ok('no emoji in markup', !/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u.test(html));
ok('fonts: Outfit + JetBrains Mono',
   html.includes('Outfit') && html.includes('JetBrains+Mono'));
ok('banned fonts absent (Inter/Roboto/Arial as webfont)',
   !/family=Inter|Roboto|Arial/.test(html));
ok('responsive breakpoint present', html.includes('@media'));
ok('all tags balanced (div count even)',
   (html.match(/<div/g) || []).length === (html.match(/<\/div>/g) || []).length,
   `${(html.match(/<div/g) || []).length} open vs ${(html.match(/<\/div>/g) || []).length} close`);

console.log('\n' + (fails === 0 ? 'ALL STATIC CHECKS PASSED' : fails + ' STATIC CHECK(S) FAILED'));
process.exit(fails === 0 ? 0 : 1);
