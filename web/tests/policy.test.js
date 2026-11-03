import test from "node:test";
import assert from "node:assert/strict";
import {
  policyObservation,
  predictionRows,
  completionLabel,
} from "../src/policy.js";

test("policy display uses actual recorded decision and independent completion", () => {
  const q = {
    node_id: 0,
    decision: "hybrid",
    predictions: {
      hybrid: { completion_probability: 0.8, conditional_attempts: 24 },
      symbolic: { completion_probability: 0.1, conditional_attempts: 2 },
    },
  };
  const trace = {
    nodes: [
      { id: 0, parent: null, state: { goals: [] } },
      { id: 1, parent: 0, state: null },
    ],
    retrievals: [q],
    status: "verified",
    verification: { verified: true },
  };
  assert.equal(policyObservation(trace, 1), q);
  assert.deepEqual(predictionRows(q)[0], {
    mode: "hybrid",
    probability: 0.8,
    cost: 24,
    selected: true,
  });
  assert.equal(completionLabel(trace), "Independently verified");
});
test("unexpanded states do not receive invented choices or probabilities", () => {
  assert.equal(
    policyObservation(
      { nodes: [{ id: 8, state: { goals: [] } }], retrievals: [] },
      8,
    ),
    null,
  );
  assert.deepEqual(
    predictionRows({ predicted_log_costs: { symbolic: 2 } }),
    [],
  );
});
test("bounded noncompletion is not mathematical falsity or a verified proof", () => {
  assert.equal(
    completionLabel({
      status: "not_found_within_budget",
      verification: { verified: false },
    }),
    "Not completed within budget",
  );
  assert.notEqual(
    completionLabel({ status: "verified", verification: { verified: false } }),
    "Independently verified",
  );
  assert.equal(completionLabel(null), "Unobserved");
});
