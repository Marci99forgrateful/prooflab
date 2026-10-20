import test from "node:test";
import assert from "node:assert/strict";
import { candidateEvidence, retrievalRows } from "../src/premises.js";

const trace = {
  nodes: [
    { id: 0, parent: null, status: "root" },
    {
      id: 1,
      parent: 0,
      tactic: "exists (f a)",
      status: "accepted",
      on_proof_path: true,
    },
    {
      id: 2,
      parent: 0,
      tactic: "apply h",
      status: "accepted",
      on_proof_path: false,
    },
    {
      id: 3,
      parent: 0,
      tactic: "rfl",
      status: "rejected",
      error: "not definitionally equal",
    },
  ],
  verification: { verified: true },
  retrievals: [
    {
      node_id: 0,
      mode: "typed",
      selected: ["exists (f a)", "apply h", "rfl"],
      original: ["apply h", "rfl"],
      pool: [
        {
          candidate: { tactic: "exists (f a)", prior: 7 },
          family: "witness",
          compatible: true,
          term: "f a",
          construction_depth: 1,
          deterministic_score: 13,
        },
      ],
      native: {
        rows: [
          {
            tactic: "exists (f a)",
            family: "witness",
            type: "β",
            compatible: true,
          },
          {
            tactic: "apply And.left",
            declaration: "And.left",
            compatible: true,
            premises: ["R ∧ ?b"],
          },
        ],
      },
    },
  ],
  rankings: [
    {
      node_id: 0,
      candidates: [
        {
          tactic: "exists (f a)",
          actual_rank: 1,
          heuristic_score: 7,
          outcome_score: 0.4,
        },
      ],
    },
  ],
};

test("availability, actual applicability and complete-proof evidence stay distinct", () => {
  assert.match(
    candidateEvidence(trace, 0, { tactic: "exists (f a)" }),
    /verified complete proof/,
  );
  assert.match(
    candidateEvidence(trace, 0, { tactic: "apply h" }),
    /outcome unknown/,
  );
  assert.match(candidateEvidence(trace, 0, { tactic: "rfl" }), /Lean rejected/);
  assert.match(
    candidateEvidence(trace, 0, { tactic: "apply And.left" }),
    /Unexplored/,
  );
});

test("native types merge by canonical declaration without inventing ranks", () => {
  const { rows } = retrievalRows(trace, 0, [
    {
      name: "And.left",
      type: "∀ {a b : Prop}, a ∧ b → a",
      source_module: "Init.Prelude",
    },
  ]);
  const witness = rows.find((r) => r.tactic === "exists (f a)");
  assert.equal(witness.type, "β");
  assert.equal(witness.actual_rank, 1);
  assert.equal(witness.selected, true);
  const lemma = rows.find((r) => r.tactic === "apply And.left");
  assert.equal(lemma.selected, false);
  assert.equal(lemma.actual_rank, undefined);
  assert.equal(lemma.compatible, true);
  assert.match(lemma.type, /Prop/);
  assert.match(lemma.evidence, /Unexplored/);
  assert.equal(retrievalRows(trace, 99).query, null);
});
