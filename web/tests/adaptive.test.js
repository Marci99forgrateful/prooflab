import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { adaptiveEvidence } from "../src/adaptive.js";
import { retrievalRows } from "../src/premises.js";

function actual(name) {
  return JSON.parse(
    gunzipSync(
      readFileSync(
        new URL(
          `../../experiments/phase6/pilot-v1/traces/${name}.json.gz`,
          import.meta.url,
        ),
      ),
    ),
  );
}

test("adaptive panel uses the actual native policy, allocation and attempts", () => {
  const trace = actual("p6_dev_curried_construction_02--deterministic");
  const query = trace.retrievals[0];
  const html = adaptiveEvidence(query, trace, 0);
  assert.match(html, /hybrid/);
  assert.match(html, /Deterministic mathematical-context decision/);
  assert.ok(
    html.includes(`${query.allocation.baseline} / ${query.allocation.novelty}`),
  );
  const row = retrievalRows(trace, 0).rows.find((r) => r.term === "f a b");
  assert.ok(row.selected && row.compatible);
  assert.match(row.evidence, /independently verified complete proof/);
});

test("unqueried symbolic availability remains unknown", () => {
  const trace = actual("p6_dev_ring_expansion_05--deterministic");
  const query = trace.retrievals[0];
  assert.equal(query.decision, "symbolic");
  assert.match(
    adaptiveEvidence(query, trace, 0),
    /Unqueried typed availability and relevance remain unknown/,
  );
  assert.equal(query.native, undefined);
});

test("historical records do not receive invented adaptive decisions", () => {
  assert.equal(adaptiveEvidence({ mode: "typed" }, { nodes: [] }, 0), "");
});

test("learned mode display uses recorded costs and separates retrieval from execution", () => {
  const index = JSON.parse(
    readFileSync(new URL("../public/phase6/explorer.json", import.meta.url)),
  );
  const entry = index.manifest.find((e) => e.arm === "learned");
  const trace = JSON.parse(
    gunzipSync(
      readFileSync(new URL(`../public/${entry.url}`, import.meta.url)),
    ),
  );
  const query = trace.retrievals.find((q) => q.predicted_log_costs);
  assert.ok(query);
  const expected = Object.entries(query.predicted_log_costs).sort(
    ([a, x], [b, y]) => x - y || a.localeCompare(b),
  )[0][0];
  assert.equal(query.decision, expected);
  const html = adaptiveEvidence(query, trace, query.node_id);
  for (const cost of Object.values(query.predicted_log_costs))
    assert.ok(html.includes(cost.toFixed(5)));
  assert.match(html, /success-conditioned selection bias/);
  assert.match(html, /Retrieval selects availability/);
  for (const row of retrievalRows(trace, query.node_id).rows) {
    const actual = trace.rankings
      .find((r) => r.node_id === query.node_id)
      ?.candidates.find((c) => c.tactic === row.tactic);
    assert.equal(row.actual_rank, actual?.actual_rank);
  }
});
