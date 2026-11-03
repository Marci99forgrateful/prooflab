import { escapeHtml as esc, treeMarkup } from "./tree.js";
import { recordedJson, neighborhood } from "./architecture.js";

const $ = (selector) => document.querySelector(selector);
let base = "",
  index = null,
  epoch = 0;
let traces = [null, null],
  selected = [0, 0],
  whole = [false, false];
let liveJob = null;
const names = {
  phase4: "Phase 4 · strongest symbolic",
  phase6_staged: "Phase 6 · staged hybrid",
  phase6_learned: "Phase 6 · conditional cost",
  completion: "Phase 7 · completion probability",
  cost: "Phase 7 · conditional cost only",
  joint: "Phase 7 · joint success / cost",
  conservative: "Phase 7 · conservative learned",
  root_trained: "Phase 7 · root-trained ablation",
  staged: "Phase 7 · staged engine control",
  automation: "Native Aesop reference",
  grind: "Native grind reference",
  symbolic: "Symbolic expert",
  hybrid: "Hybrid expert",
  typed: "Typed expert",
};

export function policyObservation(trace, nodeId) {
  const node = trace?.nodes?.find((n) => n.id === Number(nodeId));
  const source = node?.state ? node.id : node?.parent;
  return trace?.retrievals?.find((q) => q.node_id === source) || null;
}
export function predictionRows(observation) {
  return Object.entries(observation?.predictions || {}).map(([mode, p]) => ({
    mode,
    probability: p.completion_probability,
    cost: p.conditional_attempts,
    selected: observation.decision === mode,
  }));
}
export function completionLabel(trace) {
  if (trace?.status === "verified" && trace?.verification?.verified)
    return "Independently verified";
  if (trace?.status === "not_found_within_budget")
    return "Not completed within budget";
  return trace?.status || "Unobserved";
}
export function initializePolicy(value) {
  base = value;
}
function entries() {
  return index.manifest.filter(
    (r) =>
      r.role === $("#policy-source").value &&
      r.task_id === $("#policy-task").value &&
      (r.role !== "development" ||
        `${r.source_state}:${r.budget_level}` === $("#policy-horizon").value),
  );
}
function fillPolicies() {
  const rows = entries();
  [0, 1].forEach((side) => {
    const select = $(`#policy-arm-${side}`),
      previous = select.value;
    select.innerHTML = [...new Set(rows.map((r) => r.arm))]
      .map(
        (arm) =>
          `<option value="${esc(arm)}">${esc(names[arm] || arm)}</option>`,
      )
      .join("");
    const preferred = side === 0 ? "conservative" : "phase6_staged";
    select.value = rows.some((r) => r.arm === previous)
      ? previous
      : rows.some((r) => r.arm === preferred)
        ? preferred
        : rows[Math.min(side, rows.length - 1)]?.arm;
  });
  $("#policy-horizon-label").hidden =
    $("#policy-source").value !== "development";
  $("#policy-live").hidden =
    $("#policy-source").value !== "evaluation" ||
    !$("#mode-toggle").dataset.available;
  loadPair();
}
function fillHorizons() {
  const rows = index.manifest.filter(
    (r) =>
      r.role === $("#policy-source").value &&
      r.task_id === $("#policy-task").value,
  );
  $("#policy-horizon").innerHTML = [
    ...new Set(rows.map((r) => `${r.source_state}:${r.budget_level}`)),
  ]
    .map((key) => {
      const row = rows.find(
        (r) => `${r.source_state}:${r.budget_level}` === key,
      );
      return `<option value="${key}">${row.source_state === 0 ? "Initial" : "Intermediate"} state · ${row.attempt_budget} attempts / ${row.wall_budget}s</option>`;
    })
    .join("");
  fillPolicies();
}
function fillTasks() {
  const role = $("#policy-source").value;
  const ids = [
    ...new Set(
      index.manifest.filter((r) => r.role === role).map((r) => r.task_id),
    ),
  ];
  $("#policy-task").innerHTML = ids
    .map(
      (id) =>
        `<option value="${id}">${esc(index.tasks.find((t) => t.id === id)?.title || id)}</option>`,
    )
    .join("");
  fillHorizons();
}
function download(name, value, type = "application/json") {
  const url = URL.createObjectURL(new Blob([value], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function renderSide(side) {
  const trace = traces[side],
    container = $(`#policy-side-${side}`);
  if (!trace) return;
  container.dataset.taskId = trace.task.id;
  container.dataset.sourceState = trace.metadata.source_state || "0";
  container.dataset.budgetLevel = trace.metadata.budget_level || "evaluation";
  const node = trace.nodes[selected[side]] || trace.nodes[0];
  selected[side] = node.id;
  const state = node.state || trace.nodes[node.parent]?.state;
  const q = policyObservation(trace, node.id);
  const rows = predictionRows(q);
  const children = trace.nodes.filter((n) => n.parent === node.id);
  const visible = whole[side] ? trace.nodes : neighborhood(trace, node.id);
  const tree = treeMarkup(visible, node.id);
  const positions = [...tree.positions.values()];
  const minX = Math.min(...positions.map((p) => p.x)) - 65;
  const minY = Math.min(...positions.map((p) => p.y)) - 45;
  const width = Math.max(
    480,
    Math.max(...positions.map((p) => p.x)) - minX + 65,
  );
  const height = Math.max(
    360,
    Math.max(...positions.map((p) => p.y)) - minY + 75,
  );
  container.innerHTML = `<div class="policy-result"><span class="small-label">${esc(names[trace.metadata.arm] || trace.metadata.arm || trace.metadata.policy)}</span><h3>${esc(completionLabel(trace))}</h3><p>${trace.metrics.attempted_candidates} attempts · ${trace.metrics.expanded_states} expansions · ${trace.metrics.elapsed_s.toFixed(2)}s · ${trace.metadata.strategy_switches || 0} switches</p></div>
  <div class="policy-tree-tools"><button class="text-button policy-whole">${whole[side] ? "Show neighborhood" : "Complete actual tree"}</button><label>Zoom <input class="policy-zoom" type="range" min="0.3" max="2.5" step="0.1" value="1"></label><button class="text-button policy-export">Export full trace</button></div>
  <div class="policy-tree" tabindex="0" aria-label="Scrollable actual proof search tree"><svg viewBox="${minX} ${minY} ${width} ${height}" role="img" aria-label="Actual recorded Lean states"><g class="policy-tree-transform">${tree.markup}</g></svg></div>
  <label>Inspect actual state<select class="policy-node">${trace.nodes.map((n) => `<option value="${n.id}" ${n.id === node.id ? "selected" : ""}>${n.id} · ${esc(n.tactic || "initial state")} · ${n.status}</option>`).join("")}</select></label>
  <pre class="policy-native">${esc((state?.goals || []).map((g, i) => `GOAL ${i + 1}\n${g.hypotheses.map((h) => `${h.name} : ${h.type.text}`).join("\n")}\n⊢ ${g.target.text}`).join("\n\n") || "No remaining Lean goals")}</pre>
  <h3>Policy decision at this state</h3>
  ${q ? `<p class="policy-reason">${esc(q.decision_reason || q.decision_source || "Historical strategy decision")} · selected <strong>${esc(q.decision || "unrecorded")}</strong>${q.baseline_decision ? ` · staged fallback ${esc(q.baseline_decision)}` : ""}.</p>` : "<p>No policy decision was executed at this unexpanded state.</p>"}
  ${rows.length ? `<div class="policy-table-scroll"><table class="policy-predictions"><thead><tr><th>Strategy</th><th>Completion estimate</th><th>Attempts if completed</th><th>Actual selection</th></tr></thead><tbody>${rows.map((r) => `<tr><td>${esc(r.mode)}</td><td>${(100 * r.probability).toFixed(1)}%</td><td>${r.cost.toFixed(1)}</td><td>${r.selected ? "Selected" : "Alternative estimate"}</td></tr>`).join("")}</tbody></table></div><p class="method-note">Completion within the recorded budget is an operational prediction. These estimates are not proof certificates or mathematical truth labels. Conditional cost describes successful fixed-expert continuations.</p>` : q?.predicted_log_costs && Object.keys(q.predicted_log_costs).length ? `<p>Historical success-conditioned log-costs: ${esc(JSON.stringify(q.predicted_log_costs))}. No completion probabilities were estimated by this controller.</p>` : "<p>No learned completion estimates were executed in this deterministic/fixed strategy run.</p>"}
  ${q?.budget_features ? `<p>Remaining: ${(600 * q.budget_features.remaining_attempts).toFixed(0)} attempts · ${(80 * q.budget_features.remaining_expansions).toFixed(0)} expansions · ${(18 * q.budget_features.remaining_seconds).toFixed(2)} seconds. The frontier retains ${q.retained_frontier} earlier branches.</p>` : ""}
  <details><summary>Actual attempted continuations (${children.length})</summary><ul>${children.map((n) => `<li><code>${esc(n.tactic)}</code> · ${esc(n.status)}${n.on_proof_path ? " · independently verified complete proof path" : ""}${n.error ? ` · ${esc(n.error.slice(0, 250))}` : ""}</li>`).join("")}</ul><p>Accepted but uncompleted and unsearched continuations remain unresolved.</p></details>
  <details><summary>Verified proof and source prefix</summary><pre>${esc(trace.verification.verified ? trace.lean_source : "No independently verified proof was found.")}</pre><p>Restored source prefix: <code>${esc(trace.metadata.prefix || "[]")}</code></p></details>`;
  container.querySelector(".policy-node").onchange = (e) => {
    selected[side] = Number(e.target.value);
    renderSide(side);
  };
  container.querySelectorAll(".tree-node").forEach((el) => {
    const choose = () => {
      selected[side] = Number(el.dataset.node);
      renderSide(side);
    };
    el.onclick = choose;
    el.onkeydown = (e) => {
      if (e.key === "Enter") choose();
    };
  });
  container.querySelector(".policy-whole").onclick = () => {
    whole[side] = !whole[side];
    renderSide(side);
  };
  container.querySelector(".policy-zoom").oninput = (e) => {
    container.querySelector("svg").style.width =
      `${100 * Number(e.target.value)}%`;
  };
  container.querySelector(".policy-export").onclick = () =>
    download(
      `${trace.task.id}--${trace.metadata.arm}.json`,
      JSON.stringify(trace, null, 2),
    );
}
async function loadPair() {
  const current = ++epoch;
  $("#policy-notice").textContent = "Loading actual Lean traces…";
  try {
    const rows = entries();
    const loaded = await Promise.all(
      [0, 1].map(async (side) => {
        const entry = rows.find(
          (r) => r.arm === $(`#policy-arm-${side}`).value,
        );
        if (!entry)
          throw new Error("No actual run is available for this selection.");
        const response = await fetch(base + entry.url);
        if (!response.ok)
          throw new Error("Could not load the recorded execution.");
        return recordedJson(response, entry.url);
      }),
    );
    if (current !== epoch) return;
    traces = loaded;
    selected = [0, 0];
    whole = [false, false];
    [0, 1].forEach(renderSide);
    const peers = rows
      .map(
        (r) =>
          `<tr><td>${esc(names[r.arm] || r.arm)}</td><td>${esc(r.status)}</td><td>${r.attempts}</td><td>${r.wall_s.toFixed(2)}s</td></tr>`,
      )
      .join("");
    $("#policy-outcomes").innerHTML =
      `<h3>Actual matched executions</h3><div class="policy-table-scroll"><table><thead><tr><th>Strategy</th><th>Outcome</th><th>Attempts</th><th>Elapsed</th></tr></thead><tbody>${peers}</tbody></table></div><p class="method-note">Development rows restore the same original prefix at the same budget. Final policy runs share the frozen outer budget. Aesop/grind use opaque internal work.</p>`;
    $("#policy-notice").textContent =
      $("#policy-source").value === "development"
        ? "Recorded development continuations · not new held-out evidence"
        : "Frozen evaluation replay · every reported success independently checked by Lean";
  } catch (error) {
    $("#policy-notice").textContent = error.message;
  }
}
async function liveSearch() {
  $("#policy-live").disabled = true;
  document.querySelectorAll(".policy-controls select").forEach((el) => {
    el.disabled = true;
  });
  $("#policy-notice").textContent = "Computing a new local Lean proof…";
  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task_id: $("#policy-task").value,
        phase7_policy: $("#policy-arm-0").value,
        budget: index.budget,
      }),
    });
    if (!response.ok)
      throw new Error(
        "Live search requires the local backend and a registered evaluation task.",
      );
    liveJob = (await response.json()).job_id;
    $("#policy-cancel").hidden = false;
    while (liveJob) {
      await new Promise((resolve) => setTimeout(resolve, 250));
      const result = await (await fetch(`/api/jobs/${liveJob}`)).json();
      if (result.state === "running") continue;
      liveJob = null;
      if (!result.trace)
        throw new Error(result.error || "Computation ended without a trace.");
      traces[0] = result.trace;
      selected[0] = 0;
      renderSide(0);
      $("#policy-notice").textContent =
        `New local computation: ${completionLabel(result.trace)}. Recorded comparison remains on the right.`;
    }
  } catch (error) {
    $("#policy-notice").textContent = error.message;
  } finally {
    $("#policy-live").disabled = false;
    document.querySelectorAll(".policy-controls select").forEach((el) => {
      el.disabled = false;
    });
    $("#policy-cancel").hidden = true;
  }
}
export async function openPolicy() {
  if (index) return;
  try {
    const response = await fetch(base + "phase7/explorer.json");
    if (!response.ok)
      throw new Error(
        "Phase 7 replay assets are unavailable. Run the documented Phase 7 export.",
      );
    index = await response.json();
    $("#policy-source").onchange = fillTasks;
    $("#policy-task").onchange = fillHorizons;
    $("#policy-horizon").onchange = fillPolicies;
    [0, 1].forEach((side) => {
      $(`#policy-arm-${side}`).onchange = loadPair;
    });
    $("#policy-live").onclick = liveSearch;
    $("#policy-cancel").onclick = () => {
      if (liveJob) fetch(`/api/jobs/${liveJob}`, { method: "DELETE" });
    };
    const comparison =
      index.summary.comparisons["conservative minus phase6_staged"];
    $("#policy-results").innerHTML =
      `<h2>Frozen mathematical evaluation</h2><div class="policy-table-scroll"><table><thead><tr><th>Policy</th><th>Verified / 48</th><th>Mean attempts</th><th>Mean wall time</th></tr></thead><tbody>${Object.entries(
        index.summary.results,
      )
        .map(
          ([arm, r]) =>
            `<tr><td>${esc(names[arm] || arm)}</td><td>${r.verified}/48</td><td>${r.means.attempts.toFixed(1)}</td><td>${r.means.wall_s.toFixed(2)}s</td></tr>`,
        )
        .join(
          "",
        )}</tbody></table></div><p class="method-note">Primary conservative minus Phase 6 staged: ${(100 * comparison.theorem_interval.estimate).toFixed(1)} percentage points; paired theorem 95% interval [${(100 * comparison.theorem_interval.lower).toFixed(1)}, ${(100 * comparison.theorem_interval.upper).toFixed(1)}]. Family sensitivity [${(100 * comparison.family_interval.lower).toFixed(1)}, ${(100 * comparison.family_interval.upper).toFixed(1)}]. Training loss alone does not establish a search improvement.</p>`;
    fillTasks();
  } catch (error) {
    $("#policy-notice").textContent = error.message;
    index = null;
  }
}
