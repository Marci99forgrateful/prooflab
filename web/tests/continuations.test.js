import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { classifyContinuation } from "../src/continuations.js";
const root = new URL(
  "../../experiments/phase3/continuations-v1/tasks/",
  import.meta.url,
);
const examples = readdirSync(root).flatMap((name) =>
  JSON.parse(readFileSync(new URL(name, root), "utf8")).states.flatMap(
    (s) => s.observations,
  ),
);

test("actual verified alternatives require a completed independent audit", () => {
  const o = examples.find((o) => o.continuation?.verification.verified);
  assert.ok(o);
  assert.equal(classifyContinuation(o).kind, "verified");
});
test("actual bounded unresolved continuations stay separate from invalid tactics", () => {
  const censored = examples.find((o) => o.continuation?.status === "censored");
  const invalid = examples.find((o) => o.status === "invalid_candidate");
  assert.ok(censored);
  assert.ok(invalid);
  assert.equal(classifyContinuation(censored).kind, "censored");
  assert.equal(classifyContinuation(invalid).kind, "invalid");
});
test("actual unexamined valid actions are not displayed as failures", () => {
  const o = examples.find((o) => o.status === "accepted" && !o.continuation);
  assert.ok(o);
  assert.equal(classifyContinuation(o).kind, "unexplored");
});
