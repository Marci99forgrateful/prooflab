import test from "node:test";
import assert from "node:assert/strict";
import { escapeHtml, layoutTree, treeMarkup } from "../src/tree.js";

test("layout preserves recorded parent/depth structure", () => {
  const nodes = [
    { id: 0, parent: null, depth: 0 },
    { id: 1, parent: 0, depth: 1 },
    { id: 2, parent: 0, depth: 1 },
    { id: 3, parent: 1, depth: 2 },
  ];
  const p = layoutTree(nodes);
  assert.equal(p.get(3).y, 224);
  assert.equal(p.get(0).x, (p.get(1).x + p.get(2).x) / 2);
  assert.notEqual(p.get(1).x, p.get(2).x);
});
test("all nodes and edges come from the input trace", () => {
  const nodes = [
    { id: 0, parent: null, depth: 0, status: "root" },
    {
      id: 1,
      parent: 0,
      depth: 1,
      status: "rejected",
      tactic: "<script>alert(1)</script>",
    },
  ];
  const { markup } = treeMarkup(nodes);
  assert.equal((markup.match(/data-node=/g) || []).length, 2);
  assert.equal((markup.match(/<path /g) || []).length, 1);
  assert.ok(!markup.includes("<script>"));
  assert.match(markup, /rejected/);
});
test("escape handles all HTML special characters", () => {
  assert.equal(escapeHtml('<a x="&\'">'), "&lt;a x=&quot;&amp;&#39;&quot;&gt;");
});
test("empty traces render no invented nodes", () => {
  assert.equal(treeMarkup([]).markup, "");
});
