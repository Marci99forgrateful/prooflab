import { escapeHtml as esc, layoutTree, treeMarkup } from "./tree.js";
import { renderPremises } from "./premises.js";

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
let dataset = "phase4";
let labels = policyNames;
let base = "",
  manifest = [],
  index = null,
  traces = [],
  epoch = 0;
let wholeTrees = [false, false];
let localJob = null;
let preferredRepeat = null;
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
export async function recordedJson(response, url) {
  if (!url.endsWith(".gz")) return response.json();
  const bytes = new Uint8Array(await response.arrayBuffer());
  // Fetch may already decode Content-Encoding. Inspect actual bytes rather
  // than assuming a particular static host's .gz MIME/encoding policy.
  if (bytes[0] === 31 && bytes[1] === 139) {
    const plain = new Blob([bytes])
      .stream()
      .pipeThrough(new DecompressionStream("gzip"));
    return new Response(plain).json();
  }
  return JSON.parse(new TextDecoder().decode(bytes));
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
    ? `<p>Insertion priority <strong>${value.priority.toFixed(6)}</strong> · predicted log continuation cost <strong>${value.learned_value.toFixed(6)}</strong> · original heuristic ${value.heuristic_priority.toFixed(3)}.</p><p class="method-note">Actual policy: ${esc(labels[trace.metadata.arm] || labels[trace.algorithm])}. Lower priority is selected first; only learned-frontier policies use the model value for scheduling. Their priority is clamped log-cost plus 0.15 × depth. The predicted value is conditional on successful development continuations; it is not a probability or certificate.</p><p class="method-note">Top eight weighted, standardized feature contributions:</p><div class="arch-terms">${value.contributions.map(([n, v]) => `<span><code>${esc(n)}</code> ${v >= 0 ? "+" : ""}${v.toFixed(5)}</span>`).join("")}</div>`
    : "<p>Rejected/closed states are not inserted into the frontier; no state value is recorded for them.</p>";
  if (dataset !== "phase4" && value) {
    const panel = container.querySelector(".arch-value");
    panel.innerHTML = `<details><summary>Frontier score and contributions</summary>${panel.innerHTML}</details>`;
  }
  container.querySelector(".arch-path").textContent =
    prefixOf(trace, id).join("\n") || "Initial native state";
  container.querySelector(".arch-candidates").innerHTML = ranking
    ? `<table><thead><tr><th>Actual rank</th><th>Tactic</th><th>Handcrafted</th><th>Phase 2</th><th>Phase 3</th></tr></thead><tbody>${ranking.candidates.map((c) => `<tr><td>${c.actual_rank}</td><td><code>${esc(c.tactic)}</code></td><td>${c.heuristic_score}</td><td>${c.learned_score?.toFixed(5) ?? "—"}</td><td>${c.outcome_score?.toFixed(5) ?? "—"}</td></tr>`).join("")}</tbody></table><p class="method-note">This is the complete bounded pool generated from the inspected native state. Absence from this pool is a generator limitation, not evidence that a tactic is impossible. Larger candidate scores rank first; frontier scores use the opposite direction.</p>`
    : "<p>This state was not expanded, or this reference delegates its internal candidate search.</p>";
  renderPremises(
    container.querySelector(".arch-premises"),
    trace,
    sourceNode,
    index?.declarations || [],
  );
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
  container.innerHTML = `<div class="card-top"><h2>${esc(labels[t.metadata.arm] || labels[t.algorithm])}</h2><span class="pill">${esc(t.status)}</span></div>
    <div class="arch-metrics"><span><b>${m.attempted_candidates}</b>attempts</span><span><b>${m.expanded_states}</b>expanded</span><span><b>${t.nodes.length}</b>tree nodes</span><span><b>${Number(t.metadata.runner_wall_s ?? m.elapsed_s).toFixed(3)}s</b>${t.metadata.runner_wall_s ? "full call" : "wall"}</span><span><b>${m.lean_execution_s.toFixed(3)}s</b>Lean</span><span><b>${m.planning_s.toFixed(3)}s</b>planning</span><span><b>${m.model_inference_s.toFixed(3)}s</b>scores/explanations</span><span><b>${t.beam_evictions?.length || 0}</b>beam evictions</span></div>
    ${t.retrievals?.length || m.retrieval_queries ? `<p class="method-note">Retrieval ${m.retrieval_s.toFixed(4)}s · ${m.retrieval_queries} native queries${t.metadata.failed_retrieval_queries !== undefined ? ` · ${esc(t.metadata.failed_retrieval_queries)} failed queries` : ""} · ${m.declaration_probes} returned declaration probes · ${m.term_constructions} returned term construction attempts · ${m.retrieval_heartbeats} retrieval / ${m.tactic_heartbeats} tactic allocation heartbeats. Session CPU ${m.session_cpu_s?.toFixed(3) ?? "unavailable"}s · summed process RSS high-water bound ${m.session_peak_rss_kib ?? "unavailable"} KiB; independent audit resources excluded. Interrupted native counters can be unavailable.</p>` : ""}
    <p class="method-note">${esc(t.termination)} · ${m.proof_length} proof steps · source ${esc(t.metadata.code_commit.slice(0, 12))}. ${["automation", "grind"].includes(t.algorithm) ? "External tactic reference: internal state/candidate work is not comparable to ProofLab counts." : `Recorded budget: ${t.budget.timeout_s}s engine wall, ${t.budget.max_attempts} attempts, ${t.budget.max_expansions} expansions, depth ${t.budget.max_depth}, cap ${t.budget.max_candidates}.`}</p>
    <div class="arch-tree-controls"><button class="text-button arch-zoom-in">Zoom +</button><button class="text-button arch-zoom-out">Zoom −</button><button class="text-button arch-fit">Fit all</button><button class="text-button arch-whole">Complete tree</button><button class="text-button arch-focus">Focus inspected state</button></div>
    <div class="tree-container arch-tree"><svg viewBox="0 0 700 360" aria-label="Actual search architecture tree"><g class="arch-transform">${markup}</g></svg></div>
    <p class="method-note arch-tree-note"></p><div class="arch-decision"></div><div class="arch-queue table-scroll"></div>
    <details open><summary class="arch-state-title">Native state</summary><div class="arch-value"></div><pre class="arch-state continuation-code"></pre><pre class="arch-error continuation-code"></pre></details>
    <details><summary>Actual path to inspected state</summary><pre class="arch-path continuation-code"></pre></details>
    <details><summary>Candidate availability and policy rankings</summary><div class="arch-candidates table-scroll"></div></details>
    <details open><summary>Premise & Candidate Explorer</summary><div class="arch-premises"></div></details>
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
    const task = $("#arch-task").value;
    const policies = [$("#arch-policy-a").value, $("#arch-policy-b").value];
    const available = manifest
      .filter((e) => e.task_id === task)
      .filter((e) =>
        policies.every((policy) =>
          manifest.some(
            (other) =>
              other.task_id === task &&
              (dataset === "phase4" ? other.algorithm : other.arm) === policy &&
              other.repeat === e.repeat,
          ),
        ),
      )
      .map((e) => e.repeat);
    const repeats = [...new Set(available)].sort((a, b) => a - b);
    const previousRepeat = preferredRepeat ?? Number($("#arch-repeat").value);
    preferredRepeat = null;
    $("#arch-repeat").innerHTML = repeats
      .map((r) => `<option value="${r}">Run ${r + 1}</option>`)
      .join("");
    const repeat = repeats.includes(previousRepeat)
      ? previousRepeat
      : repeats[0];
    $("#arch-repeat").value = repeat;
    const next = await Promise.all(
      policies.map(async (algorithm) => {
        const e = manifest.find(
          (e) =>
            e.task_id === task &&
            (dataset !== "phase4"
              ? e.arm === algorithm
              : e.algorithm === algorithm) &&
            e.repeat === repeat,
        );
        if (!e) throw new Error("This execution is unavailable");
        const response = await fetch(base + e.url);
        if (!response.ok) throw new Error("Recorded trace could not be loaded");
        return recordedJson(response, e.url);
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
    $("#arch-notice").textContent =
      JSON.stringify(traces[0].budget) === JSON.stringify(traces[1].budget)
        ? ""
        : "These recordings use different budgets. This is a descriptive comparison, not an equal-budget result.";
    const limitation = index?.limitations?.[task];
    $("#arch-limitations").textContent =
      limitation ||
      (dataset !== "phase4"
        ? "Fixed cap 24; selection and resource costs are recorded per expanded state. Native retrieval and model inference count within the same wall budget. Phase 6 uses explicit P3 score/tactic-string ordering, independent of retrieval input order. Aesop/grind remain separate references."
        : "Original fixed candidate generator: at most 24 tactics from a 24-lemma index and structural/local-context proposals. The separate generator investigation changes candidate availability and is excluded from these primary traces.");
  } catch (error) {
    $("#arch-notice").textContent = error.message;
  }
}
export async function openArchitecture() {
  if (manifest.length) return;
  try {
    const requestedDataset = dataset;
    const result = await fetch(base + requestedDataset + "/explorer.json");
    if (!result.ok)
      throw new Error(
        "Recorded assets are unavailable. Run the documented export command for this experiment.",
      );
    const received = await result.json();
    if (requestedDataset !== dataset) return;
    index = received;
    labels = index.policy_names || policyNames;
    if (dataset === "phase6")
      $("#arch-intro").innerHTML =
        `<p>${index.tasks.length} frozen held-out statements · ${new Set(Object.values(index.families || {})).size} mathematical families · ${index.summary.runs} actual executions. Compare the strongest Phase 4 symbolic search, Phase 5 retrieval and adaptive hybrid search.</p><p class="method-note">Every selected policy, budget allocation, witness, score and outcome below comes from its real execution. Mode predictions estimate cost conditional on development success; they do not certify a proof or predict mathematical impossibility.</p>`;
    else if (dataset === "phase5")
      $("#arch-intro").innerHTML =
        `<p>40 original held-out statements · ten families · 1120 actual runs across candidate generation and search scheduling. Inspect native types, typed witnesses, capped selection and actual Lean outcomes in each state below.</p><p class="method-note">Primary arms have two recorded runs, ablations one. Native Aesop/grind are separate references. Compatibility and accepted transitions do not establish useful proof progress; only fresh audited complete paths are verified.</p>`;
    else
      $("#arch-intro").innerHTML =
        `<p>32 original held-out statements · eight mathematical families · two recorded runs per architecture. Every displayed state, tree, proof and metric derives from genuine execution.</p><p class="method-note">Original fixed candidate set. Learned values do not certify proofs. Select Phase 5 or Phase 6 above for the integrated retrieval and adaptive explorers.</p>`;
    if (dataset !== "phase4") {
      $("#arch-summary").innerHTML =
        `<table><thead><tr><th>Generator × scheduler</th><th>Verified</th><th>Mean attempts</th><th>Mean wall</th><th>Mean retrieval</th></tr></thead><tbody>${Object.entries(
          index.summary.results,
        )
          .map(
            ([name, row]) =>
              `<tr><td>${esc(labels[name])}</td><td>${row.verified}/${row.runs}</td><td>${["automation", "grind"].includes(name) ? "external call" : row.metrics.attempted_candidates.mean.toFixed(2)}</td><td>${(row.metrics.runner_wall_s?.mean ?? row.metrics.elapsed_s.mean).toFixed(3)}s</td><td>${row.metrics.retrieval_s.mean.toFixed(3)}s</td></tr>`,
          )
          .join(
            "",
          )}</tbody></table><p class="method-note">All-run effort combines successes and bounded failures. Confidence intervals, paired common-verified comparisons, family analysis and negative results are in the selected experiment report.</p>`;
    } else {
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
    }

    const casePanel = $("#arch-cases");
    casePanel.hidden = dataset === "phase4";
    casePanel.innerHTML =
      dataset !== "phase4"
        ? `<details><summary>Actual gains and regressions · inspect recorded examples</summary><p class="method-note">Examples selected after evaluation for inspection; they never changed the frozen model or search. Each button loads the actual compared executions, including failed trees. Native-reference attempt counts mean external calls with different internal work.</p><div class="arch-examples">${(index.examples || []).map((e, i) => `<article><h3>${esc(e.title)}</h3><p class="method-note">${esc(e.task_id)} · ${esc(e.family)}<br/>${esc(labels[e.left])}: ${e.left_verified}/${e.repetitions} verified<br/>${esc(labels[e.right])}: ${e.right_verified}/${e.repetitions} verified${e.left_attempt_mean !== undefined ? `<br/>Mean attempts/calls ${e.left_attempt_mean.toFixed(2)} / ${e.right_attempt_mean.toFixed(2)}` : ""}</p><button class="text-button arch-example" data-example="${i}">Inspect genuine comparison ↗</button></article>`).join("")}</div></details>`
        : "";
    casePanel.querySelectorAll(".arch-example").forEach(
      (el) =>
        (el.onclick = async () => {
          const example = index.examples[Number(el.dataset.example)];
          $("#arch-task").value = example.task_id;
          $("#arch-policy-a").value = example.left;
          $("#arch-policy-b").value = example.right;
          preferredRepeat = example.repeat ?? 0;
          await loadComparison();
        }),
    );
    manifest = index.manifest;
    $("#arch-task").innerHTML = index.tasks
      .map(
        (t) =>
          `<option value="${t.id}">${esc(t.title)} · ${esc(t.domain)}</option>`,
      )
      .join("");
    for (const side of ["a", "b"])
      $("#arch-policy-" + side).innerHTML = Object.entries(labels)
        .map(([id, name]) => `<option value="${id}">${esc(name)}</option>`)
        .join("");
    $("#arch-policy-a").value =
      dataset === "phase6"
        ? "phase4"
        : dataset === "phase5"
          ? "original_p3"
          : "best_first";
    $("#arch-policy-b").value =
      dataset === "phase6"
        ? "learned"
        : dataset === "phase5"
          ? "learned_p3"
          : "joint";
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
  $("#arch-dataset").onchange = async () => {
    dataset = $("#arch-dataset").value;
    ++epoch;
    manifest = [];
    index = null;
    await openArchitecture();
  };
  $("#arch-local").onclick = async () => {
    const notice = $("#arch-notice");
    $("#arch-local").disabled = true;
    document
      .querySelectorAll(".arch-controls select")
      .forEach((el) => (el.disabled = true));
    try {
      const health = await fetch(base + "api/health");
      if (
        !health.ok ||
        !health.headers.get("content-type")?.includes("application/json") ||
        !(await health.json()).service
      )
        throw new Error(
          "Local computation needs the loopback ProofLab server; recorded replay remains available.",
        );
      const chosen = $("#arch-policy-a").value;
      const arm = index?.protocol?.arms?.find((a) => a.id === chosen);
      const response = await fetch(base + "api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_id: $("#arch-task").value,
          algorithm:
            dataset === "phase6"
              ? ["automation", "grind"].includes(arm?.mode)
                ? arm.mode
                : "outcome"
              : arm?.algorithm || chosen,
          phase6_mode: dataset === "phase6" ? arm?.mode : undefined,
          phase6_model:
            dataset === "phase6" ? arm?.model_variant || "selected" : undefined,
          generator_mode: arm?.generator || "original",
          budget: (dataset === "phase6"
            ? index?.protocol?.budgets?.[arm?.budget_level]
            : index?.protocol?.budget) ||
            traces[0]?.budget || {
              max_depth: 12,
              max_expansions: 80,
              max_candidates: 24,
              max_attempts: 600,
              timeout_s: 18,
              tactic_timeout_s: 2,
            },
        }),
      });
      if (!response.ok)
        throw new Error(`Local search could not start (${response.status})`);
      localJob = (await response.json()).job_id;
      $("#arch-local").disabled = true;
      document
        .querySelectorAll(".arch-controls select")
        .forEach((el) => (el.disabled = true));
      $("#arch-cancel").hidden = false;
      notice.textContent =
        "Running genuine local Lean search for the left policy…";
      const poll = async () => {
        try {
          const result = await (
            await fetch(base + "api/jobs/" + localJob)
          ).json();
          if (result.state === "running") {
            setTimeout(poll, 400);
            return;
          }
          if (!result.trace)
            throw new Error(
              result.error || "Local execution returned no trace",
            );
          traces[0] = result.trace;
          traces[0].metadata.arm = chosen;
          selected[0] = 0;
          wholeTrees[0] = false;
          renderSide(0);
          $("#arch-step").max = Math.max(
            0,
            ...traces.map((t) => t.frontier_decisions.length - 1),
          );
          $("#arch-step").value = 0;
          renderDecisions();
          notice.textContent = `Actual local run: ${result.trace.status} · ${result.trace.metrics.attempted_candidates} attempts. The right side remains the recorded execution. Export includes both sources.`;
        } catch (error) {
          notice.textContent = error.message;
        } finally {
          if (!notice.textContent.startsWith("Running")) {
            localJob = null;
            $("#arch-local").disabled = false;
            document
              .querySelectorAll(".arch-controls select")
              .forEach((el) => (el.disabled = false));
            $("#arch-cancel").hidden = true;
          }
        }
      };
      setTimeout(poll, 400);
    } catch (error) {
      notice.textContent = error.message;
      $("#arch-local").disabled = false;
      document
        .querySelectorAll(".arch-controls select")
        .forEach((el) => (el.disabled = false));
    }
  };
  $("#arch-cancel").onclick = async () => {
    if (localJob)
      await fetch(base + "api/jobs/" + localJob, { method: "DELETE" });
  };
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
