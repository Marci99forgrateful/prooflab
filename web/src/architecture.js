import { escapeHtml as esc, layoutTree, treeMarkup } from "./tree.js";

const $ = (s) => document.querySelector(s);
export const policyNames = {
  bfs: "Breadth-first",
  best_first: "Handcrafted",
  learned: "Phase 2 candidate policy",
  outcome: "Phase 3 candidate policy",
  frontier: "Learned frontier + handcrafted candidates",
  joint: "Learned frontier + Phase 3 candidates",
  beam: "Bounded best-first beam",
  linear_frontier: "Linear frontier control",
  automation: "Native Aesop reference",
  grind: "Native grind reference",
};
let base = "",
  manifest = [],
  index = null,
  traces = [],
  epoch = 0;
let wholeTrees = [false, false];
let selected = [0, 0],
  currentStep = 0;

export function decisionAt(trace, step) {
  const decisions = trace?.frontier_decisions || [];
  return decisions[Math.min(step, decisions.length - 1)] || null;
}
export function prefixOf(trace, id) {
  const result = [];
  for (
    let n = trace.nodes[id];
    n?.parent !== null && n;
    n = trace.nodes[n.parent]
  )
    result.unshift(n.tactic);
  return result;
}
function download(name, value) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function showState(side, id) {
  const trace = traces[side],
    container = $(`#arch-side-${side}`),
    node = trace.nodes[id];
  if (!node) return;
  selected[side] = id;
  if (!wholeTrees[side]) paintTree(side);
  const state = node.state || trace.nodes[node.parent]?.state;
  const value = trace.state_values?.find((v) => v.node_id === id);
  const sourceNode = node.state ? id : node.parent;
  const ranking = trace.rankings?.find((r) => r.node_id === sourceNode);
  container
    .querySelectorAll(".arch-node")
    .forEach((el) =>
      el.classList.toggle("selected-node", Number(el.dataset.node) === id),
    );
  container.querySelector(".arch-state-title").textContent =
    `State ${id} · ${node.tactic || "initial goal"} · ${node.status}`;
  container.querySelector(".arch-state").textContent =
    (state?.goals || [])
      .map(
        (g, i) =>
          `GOAL ${i + 1}\n${g.hypotheses.map((h) => `${h.name} : ${h.type.text}`).join("\n")}\n⊢ ${g.target.text}`,
      )
      .join("\n\n") || "No remaining native goals";
  container.querySelector(".arch-error").textContent = node.error || "";
  container.querySelector(".arch-value").innerHTML = value
    ? `<p>Insertion priority <strong>${value.priority.toFixed(6)}</strong> · predicted log continuation cost <strong>${value.learned_value.toFixed(6)}</strong> · original heuristic ${value.heuristic_priority.toFixed(3)}.</p><p class="method-note">Actual policy: ${esc(policyNames[trace.algorithm])}. Lower priority is selected first; only learned-frontier policies use the model value for scheduling. Their priority is clamped log-cost plus 0.15 × depth. The predicted value is conditional on successful development continuations; it is not a probability or certificate.</p><p class="method-note">Top eight weighted, standardized feature contributions:</p><div class="arch-terms">${value.contributions.map(([n, v]) => `<span><code>${esc(n)}</code> ${v >= 0 ? "+" : ""}${v.toFixed(5)}</span>`).join("")}</div>`
    : "<p>Rejected/closed states are not inserted into the frontier; no state value is recorded for them.</p>";
  container.querySelector(".arch-path").textContent =
    prefixOf(trace, id).join("\n") || "Initial native state";
  container.querySelector(".arch-candidates").innerHTML = ranking
    ? `<table><thead><tr><th>Actual rank</th><th>Tactic</th><th>Handcrafted</th><th>Phase 2</th><th>Phase 3</th></tr></thead><tbody>${ranking.candidates.map((c) => `<tr><td>${c.actual_rank}</td><td><code>${esc(c.tactic)}</code></td><td>${c.heuristic_score}</td><td>${c.learned_score?.toFixed(5) ?? "—"}</td><td>${c.outcome_score?.toFixed(5) ?? "—"}</td></tr>`).join("")}</tbody></table><p class="method-note">This is the complete bounded pool generated from the inspected native state. Absence from this pool is a generator limitation, not evidence that a tactic is impossible. Larger candidate scores rank first; frontier scores use the opposite direction.</p>`
    : "<p>This state was not expanded, or this reference delegates its internal candidate search.</p>";
  const repeat = $(`#arch-repeat`).value,
    key = `${trace.task.id}--${trace.algorithm}--r${repeat}.json.gz`;
  const native = index?.native?.[key],
    relations =
      native?.relationships?.filter((pair) => pair.includes(id)) || [];
  container.querySelector(".arch-repeats").textContent = native
    ? `Offline native diagnostics: ${native.distinct_native_shapes} distinct sequent shapes / ${native.states} states; ${native.repeated_native_shapes} repeated shapes; ${native.unresolved_mvar_states} states with unresolved metavariables. ${relations.length ? "Related recorded state pairs: " + relations.map((p) => p.join(" ↔ ")).join(", ") : "No recorded repeat relationship for this state."} Grouping never merges states or reuses proofs.`
    : "Native expression replay diagnostics are available after export. Similar printed states are never assumed semantically interchangeable.";
}
export function neighborhood(trace, id) {
  const ids = new Set([id]);
  for (
    let n = trace.nodes[id];
    n && n.parent !== null;
    n = trace.nodes[n.parent]
  )
    ids.add(n.parent);
  const children = trace.nodes.filter((n) => n.parent === id);
  children.filter((n) => n.state).forEach((n) => ids.add(n.id));
  children
    .filter((n) => !n.state)
    .slice(0, 4)
    .forEach((n) => ids.add(n.id));
  return trace.nodes.filter((n) => ids.has(n.id));
}
function paintTree(side) {
  const container = $(`#arch-side-${side}`),
    trace = traces[side];
  const nodes = wholeTrees[side]
    ? trace.nodes
    : neighborhood(trace, selected[side]);
  container.querySelector(".arch-transform").innerHTML = treeMarkup(
    nodes,
    selected[side],
  ).markup.replaceAll('class="tree-node ', 'class="tree-node arch-node ');
  container.querySelector(".arch-tree-note").textContent = wholeTrees[side]
    ? `Complete actual search tree: all ${nodes.length} recorded nodes. Zoom or inspect through the queue.`
    : `Actual neighborhood: path, all accepted children and up to four recorded rejections (${nodes.length} nodes). Complete tree shows all ${trace.nodes.length} attempts/root nodes.`;
  container.querySelector(".arch-whole").textContent = wholeTrees[side]
    ? "Show neighborhood"
    : "Complete tree";
  wireTree(side, nodes);
}
function wireTree(side, visibleNodes) {
  const container = $(`#arch-side-${side}`),
    svg = container.querySelector("svg"),
    group = svg.querySelector(".arch-transform");
  const positions = layoutTree(visibleNodes),
    root = positions.get(0);
  let zoom = 0.65,
    x = 350 - (root?.x || 0) * zoom,
    y = 55;
  const update = () =>
    group.setAttribute("transform", `translate(${x},${y}) scale(${zoom})`);
  update();
  container.querySelector(".arch-zoom-in").onclick = () => {
    zoom *= 1.4;
    update();
  };
  container.querySelector(".arch-zoom-out").onclick = () => {
    zoom /= 1.4;
    update();
  };
  container.querySelector(".arch-fit").onclick = () => {
    const ps = [...positions.values()],
      width = Math.max(...ps.map((p) => p.x), 1) + 120,
      height = Math.max(...ps.map((p) => p.y), 1) + 160;
    zoom = Math.min(1.25, 680 / width, 330 / height);
    x = (700 - (width - 120) * zoom) / 2;
    y = 45;
    update();
  };
  container.querySelector(".arch-focus").onclick = () => {
    const p = positions.get(selected[side]);
    if (p) {
      zoom = 0.85;
      x = 350 - p.x * zoom;
      y = 120 - p.y * zoom;
      update();
    }
  };
  container.querySelector(".arch-whole").onclick = () => {
    wholeTrees[side] = !wholeTrees[side];
    paintTree(side);
  };
  container.querySelector(".arch-fit").click();
  let drag = null;
  svg.onpointerdown = (e) => {
    if (e.target.closest(".arch-node")) return;
    drag = [e.clientX, e.clientY, x, y];
    svg.setPointerCapture(e.pointerId);
  };
  svg.onpointermove = (e) => {
    if (drag) {
      const rect = svg.getBoundingClientRect();
      x = drag[2] + ((e.clientX - drag[0]) * 700) / rect.width;
      y = drag[3] + ((e.clientY - drag[1]) * 360) / rect.height;
      update();
    }
  };
  svg.onpointerup = () => {
    drag = null;
  };
  container.querySelectorAll(".arch-node").forEach((el) => {
    const hit = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    for (const [n, v] of Object.entries({
      x: -48,
      y: -24,
      width: 96,
      height: 72,
      fill: "transparent",
    }))
      hit.setAttribute(n, v);
    el.insertBefore(hit, el.firstChild);
    el.onclick = () => showState(side, Number(el.dataset.node));
    el.onkeydown = (e) => {
      if (["Enter", " "].includes(e.key)) {
        e.preventDefault();
        showState(side, Number(el.dataset.node));
      }
    };
  });
}
function renderSide(side) {
  const t = traces[side],
    m = t.metrics,
    container = $(`#arch-side-${side}`);
  const markup = treeMarkup(t.nodes, 0).markup.replaceAll(
    'class="tree-node ',
    'class="tree-node arch-node ',
  );
  container.innerHTML = `<div class="card-top"><h2>${esc(policyNames[t.algorithm])}</h2><span class="pill">${esc(t.status)}</span></div>
    <div class="arch-metrics"><span><b>${m.attempted_candidates}</b>attempts</span><span><b>${m.expanded_states}</b>expanded</span><span><b>${t.nodes.length}</b>tree nodes</span><span><b>${m.elapsed_s.toFixed(3)}s</b>wall</span><span><b>${m.lean_execution_s.toFixed(3)}s</b>Lean</span><span><b>${m.planning_s.toFixed(3)}s</b>planning</span><span><b>${m.model_inference_s.toFixed(3)}s</b>scores/explanations</span><span><b>${t.beam_evictions?.length || 0}</b>beam evictions</span></div>
    <p class="method-note">${esc(t.termination)} · ${m.proof_length} proof steps · source ${esc(t.metadata.code_commit.slice(0, 12))}. ${["automation", "grind"].includes(t.algorithm) ? "External tactic reference: internal state/candidate work is not comparable to ProofLab counts." : "Candidate cap and native search budgets are identical across controlled policies."}</p>
    <div class="arch-tree-controls"><button class="text-button arch-zoom-in">Zoom +</button><button class="text-button arch-zoom-out">Zoom −</button><button class="text-button arch-fit">Fit all</button><button class="text-button arch-whole">Complete tree</button><button class="text-button arch-focus">Focus inspected state</button></div>
    <div class="tree-container arch-tree"><svg viewBox="0 0 700 360" aria-label="Actual search architecture tree"><g class="arch-transform">${markup}</g></svg></div>
    <p class="method-note arch-tree-note"></p><div class="arch-decision"></div><div class="arch-queue table-scroll"></div>
    <details open><summary class="arch-state-title">Native state</summary><div class="arch-value"></div><pre class="arch-state continuation-code"></pre><pre class="arch-error continuation-code"></pre></details>
    <details><summary>Actual path to inspected state</summary><pre class="arch-path continuation-code"></pre></details>
    <details><summary>Candidate availability and policy rankings</summary><div class="arch-candidates table-scroll"></div></details>
    <details><summary>Beam eviction decisions</summary><p class="method-note">Removed from the bounded queue, not rejected by Lean: ${t.beam_evictions?.join(", ") || "none"}. Evicted nodes and all executed transitions remain in this tree and export. Beam truncation may discard the only proof.</p></details>
    <details><summary>Repeated-state relationships · diagnostics only</summary><p class="arch-repeats method-note"></p></details>
    <details><summary>Complete independently verified proof / audit</summary><pre class="continuation-code">${esc(t.lean_source || "No independently verified complete proof found within this budget.")}</pre><p class="method-note">${t.verification.verified ? "Fresh Lean audit passed. Axioms: " + esc(t.verification.axioms.join(", ") || "none") + ". Source SHA-256: " + esc(t.verification.source_sha256) : "No successful complete-proof audit. Bounded failure is not mathematical impossibility."}</p></details>`;
  showState(side, 0);
}
function renderDecisions() {
  currentStep = Number($("#arch-step").value);
  $("#arch-step-label").textContent = `Frontier selection ${currentStep + 1}`;
  traces.forEach((t, side) => {
    const container = $(`#arch-side-${side}`),
      d = decisionAt(t, currentStep);
    container.querySelector(".arch-decision").innerHTML = d
      ? `<h3>Selected queued state ${d.selected}</h3><p class="method-note">After ${d.attempted_candidates} actual candidate attempts · ${d.frontier.length} queued states. ${t.nodes[d.selected].depth >= t.budget.max_depth ? "Depth limit: selected but not expanded." : "Selected for candidate expansion."} This panel clamps to this run's last decision if it ended earlier.</p>`
      : "<p>No frontier decision recorded.</p>";
    container.querySelector(".arch-queue").innerHTML = d
      ? `<table><thead><tr><th>Queued state</th><th>Insertion priority ↓</th><th>Predicted log-cost</th></tr></thead><tbody>${d.frontier.map(([priority, id]) => `<tr class="${id === d.selected ? "arch-picked" : ""}"><td><button class="text-button" data-inspect="${id}">${id === d.selected ? "→ " : ""}${id}</button></td><td>${priority.toFixed(6)}</td><td>${t.state_values?.find((v) => v.node_id === id)?.learned_value.toFixed(6) ?? "—"}</td></tr>`).join("")}</tbody></table>`
      : "";
    container
      .querySelectorAll("[data-inspect]")
      .forEach(
        (el) =>
          (el.onclick = () => showState(side, Number(el.dataset.inspect))),
      );
    if (d) showState(side, d.selected);
  });
  const a = decisionAt(traces[0], currentStep),
    b = decisionAt(traces[1], currentStep);
  const pa = a ? prefixOf(traces[0], a.selected).join(" → ") : "",
    pb = b ? prefixOf(traces[1], b.selected).join(" → ") : "";
  $("#arch-divergence").textContent =
    pa === pb
      ? "At this expansion index both executions choose the same tactic prefix. Queue priorities and later candidate order may still differ."
      : `Different actual prefixes at this selection index: left [${pa || "root"}] versus right [${pb || "root"}]. These are measured scheduling/path differences; node IDs are local to each execution.`;
}
async function loadComparison() {
  const token = ++epoch;
  $("#arch-notice").textContent = "Loading recorded native executions…";
  try {
    const task = $("#arch-task").value,
      repeat = Number($("#arch-repeat").value);
    const policies = [$("#arch-policy-a").value, $("#arch-policy-b").value];
    const next = await Promise.all(
      policies.map(async (algorithm) => {
        const e = manifest.find(
          (e) =>
            e.task_id === task &&
            e.algorithm === algorithm &&
            e.repeat === repeat,
        );
        if (!e) throw new Error("This execution is unavailable");
        const response = await fetch(base + e.url);
        if (!response.ok) throw new Error("Recorded trace could not be loaded");
        return response.json();
      }),
    );
    if (token !== epoch) return;
    traces = next;
    selected = [0, 0];
    wholeTrees = [false, false];
    traces.forEach((_, side) => renderSide(side));
    $("#arch-statement").textContent =
      `${traces[0].task.binders}\n⊢ ${traces[0].task.target}`;
    $("#arch-step").max = Math.max(
      0,
      ...traces.map((t) => t.frontier_decisions.length - 1),
    );
    $("#arch-step").value = 0;
    renderDecisions();
    $("#arch-notice").textContent = "";
    const limitation = index?.limitations?.[task];
    $("#arch-limitations").textContent =
      limitation ||
      "Original fixed candidate generator: at most 24 tactics from a 24-lemma index and structural/local-context proposals. The separate generator investigation changes candidate availability and is excluded from these primary traces.";
  } catch (error) {
    $("#arch-notice").textContent = error.message;
  }
}
export async function openArchitecture() {
  if (manifest.length) return;
  try {
    const result = await fetch(base + "phase4/explorer.json");
    if (!result.ok)
      throw new Error(
        "Phase 4 assets are not exported. Run the documented Phase 4 export command.",
      );
    index = await result.json();
    $("#arch-summary").innerHTML =
      `<table><thead><tr><th>Architecture</th><th>Verified runs</th><th>Mean attempts</th><th>Mean expanded</th><th>Mean wall</th><th>Resource limits</th></tr></thead><tbody>${Object.entries(
        index.summary.results,
      )
        .map(
          ([name, row]) =>
            `<tr><td>${esc(policyNames[name])}</td><td>${row.verified}/${row.attempted}</td><td>${["automation", "grind"].includes(name) ? "1 external call" : row.mean_candidates.toFixed(2)}</td><td>${["automation", "grind"].includes(name) ? "internal work separate" : row.mean_expansions.toFixed(2)}</td><td>${row.mean_wall_s.toFixed(3)}s</td><td>${row.resource_limits}</td></tr>`,
        )
        .join(
          "",
        )}</tbody></table><p class="method-note">Each theorem has two repeated runs. Learned frontier loses a theorem relative to handcrafted scheduling. These all-run effort means mix successes and bounded failures; see the research report for common-success subsets and theorem/family uncertainty. The linear control duplicates the selected linear model and is not independent evidence.</p>`;

    manifest = index.manifest;
    $("#arch-task").innerHTML = index.tasks
      .map(
        (t) =>
          `<option value="${t.id}">${esc(t.title)} · ${esc(t.domain)}</option>`,
      )
      .join("");
    for (const side of ["a", "b"])
      $("#arch-policy-" + side).innerHTML = Object.entries(policyNames)
        .map(([id, name]) => `<option value="${id}">${esc(name)}</option>`)
        .join("");
    $("#arch-policy-a").value = "best_first";
    $("#arch-policy-b").value = "joint";
    $("#arch-research").innerHTML = index.research
      .map(
        (r) =>
          `<article><h3>${esc(r.title)}</h3><p>${esc(r.idea)}</p><a href="${esc(r.url)}" target="_blank" rel="noreferrer">Original source ↗</a><p class="method-note">${esc(r.relation)}</p></article>`,
      )
      .join("");
    for (const id of ["task", "repeat", "policy-a", "policy-b"])
      $("#arch-" + id).onchange = loadComparison;
    await loadComparison();
  } catch (error) {
    $("#arch-notice").textContent = error.message;
  }
}
export function initializeArchitecture(assetBase) {
  base = assetBase;
  $("#arch-step").oninput = renderDecisions;
  $("#arch-next").onclick = () => {
    $("#arch-step").value = Math.min(
      Number($("#arch-step").max),
      Number($("#arch-step").value) + 1,
    );
    renderDecisions();
  };
  $("#arch-export").onclick = () =>
    download("prooflab-architecture-comparison.json", {
      traces,
      expansion_index: currentStep,
      native_diagnostics: index?.native,
      notes: "Genuine executions; predicted values do not certify proofs",
    });
}
