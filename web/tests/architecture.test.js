import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  decisionAt,
  prefixOf,
  policyNames,
  neighborhood,
} from "../src/architecture.js";

const fixture = JSON.parse(
  readFileSync(
    new URL(
      "../public/phase4/data/traces/p4_cubic_pair--joint--r0.json",
      import.meta.url,
    ),
  ),
);
test("frontier replay selects recorded decisions and clamps without inventing states", () => {
  assert.equal(decisionAt(fixture, 0).selected, 0);
  assert.deepEqual(
    decisionAt(fixture, 100000),
    fixture.frontier_decisions.at(-1),
  );
  for (const decision of fixture.frontier_decisions) {
    assert.equal(decision.selected, decision.frontier[0][1]);
    assert.ok(fixture.nodes[decision.selected].state);
  }
});
test("actual tactic prefixes reconstruct native recorded parent chains", () => {
  const solved = fixture.nodes.find((n) => n.status === "solved");
  assert.deepEqual(prefixOf(fixture, solved.id), fixture.proof);
  assert.deepEqual(prefixOf(fixture, 0), []);
  assert.equal(Object.keys(policyNames).length, 10);
});

test("neighborhood is a labelled projection of genuine recorded nodes", () => {
  const decision = fixture.frontier_decisions[6];
  const projected = neighborhood(fixture, decision.selected);
  assert.ok(projected.length < fixture.nodes.length);
  assert.ok(projected.some((n) => n.id === 0));
  assert.ok(projected.some((n) => n.id === decision.selected));
  for (const node of projected) assert.equal(node, fixture.nodes[node.id]);
  for (const child of fixture.nodes.filter(
    (n) => n.parent === decision.selected && n.state,
  ))
    assert.ok(projected.includes(child));
});
