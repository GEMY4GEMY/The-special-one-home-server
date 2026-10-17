const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');

const source = fs.readFileSync('frontend/admin.js', 'utf8');

test('admin form clears stale edit mode for AI suggestions', () => {
  assert.match(source, /delete form\.dataset\.editId/);
  assert.match(source, /namedItem\("unit"\)\.value=""/);
  assert.match(source, /namedItem\("lesson"\)\.value=""/);
});

test('AI tasks handle interruption and invalid results', () => {
  assert.match(source, /task\.state==="interrupted"/);
  assert.match(source, /Array\.isArray\(task\.output\)/);
});
