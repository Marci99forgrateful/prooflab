import katex from "katex";
import "./style.css";
import {
  initializeContinuations,
  openContinuations,
  continuationKey,
  selectContinuation,
} from "./continuations.js";
import { escapeHtml as esc, layoutTree, treeMarkup } from "./tree.js";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const base = import.meta.env.BASE_URL;
const PLAY_ICON =
  '<svg class="play-glyph" viewBox="0 0 16 16" aria-hidden="true"><path d="M5 3 13 8 5 13Z"/></svg>';
const PAUSE_ICON =
  '<svg class="play-glyph" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 3h3v10H4zM10 3h3v10h-3z"/></svg>';
const state = {
  dataset: "phase1",
  repeat: 0,
  tasks: [],
  manifest: [],
  task: null,
  trace: null,
  algorithm: "best_first",
  visible: 1,
  selected: 0,
  playing: false,
  timer: null,
  mode: "replay",
  job: null,
  zoom: 1,
  tx: 0,
  ty: 0,
};
let summaryData = null;
const datasets = {};

function notice(text = "") {
  $("#notice").textContent = text;
  $("#notice").hidden = !text;
}
function download(name, text, type = "text/plain") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function latex(text) {
  return (
    "\\displaystyle " +
    text
      .replace(/([A-Za-z])\(([A-Za-z])\)/g, "$1($2)")
      .replaceAll("⊢", "\\;\\vdash\\;")
      .replaceAll("→", "\\to ")
      .replaceAll("↔", "\\leftrightarrow ")
      .replaceAll("∧", "\\land ")
      .replaceAll("∨", "\\lor ")
      .replaceAll("¬", "\\neg ")
      .replaceAll("∀", "\\forall ")
      .replaceAll("⊆", "\\subseteq ")
      .replaceAll("∩", "\\cap ")
      .replaceAll("∪", "\\cup ")
      .replaceAll("∈", "\\in ")
      .replaceAll("≤", "\\le ")
      .replaceAll("²", "^2")
      .replaceAll("³", "^3")
      .replaceAll("−", "-")
      .replaceAll("·", "\\cdot ")
  );
}
function showTheorem(task) {
  state.task = task;
  $("#domain-badge").textContent = task.domain.toUpperCase();
  $("#task-description").textContent = task.description;
  $("#difficulty").textContent = task.difficulty;
  katex.render(latex(task.display), $("#theorem-display"), {
    throwOnError: false,
    strict: false,
  });
}
function setAlgorithm(algorithm) {
  state.algorithm = algorithm;
  $$("[data-algorithm]").forEach((b) =>
    b.classList.toggle("selected", b.dataset.algorithm === algorithm),
  );
  $("#strategy-note").textContent =
    algorithm === "outcome"
      ? "Predict efficient verified continuations using the current goal and context. Same candidates; no Lean lookahead."
      : algorithm === "learned"
        ? "A locally trained pairwise model orders the same candidates. The state frontier keeps the original heuristic."
        : algorithm === "bfs"
          ? "Explore each depth in order. A deterministic, systematic baseline."
          : "Prioritize smaller goals with a transparent mathematical heuristic.";
}
async function fetchTrace(taskId, algorithm) {
  const entry = state.manifest.find(
    (t) =>
      t.task_id === taskId &&
      t.algorithm === algorithm &&
      (t.repeat ?? 0) === state.repeat,
  );
  if (!entry) return null;
  const result = await fetch(`${base}${entry.url || `traces/${entry.file}`}`);
  if (!result.ok) throw new Error("The recorded trace could not be loaded.");
  return result.json();
}
function togglePlayback(play = !state.playing) {
  state.playing = play;
  clearTimeout(state.timer);
  $("#play-toggle").innerHTML = play ? PAUSE_ICON : PLAY_ICON;
  if (play && state.trace) {
    if (state.visible >= state.trace.nodes.length) state.visible = 1;
    function tick() {
      if (!state.playing || !state.trace) return;
      state.visible = Math.min(state.visible + 1, state.trace.nodes.length);
      state.selected = state.trace.nodes[state.visible - 1].id;
      renderTree(false);
      inspect(state.selected);
      if (state.visible < state.trace.nodes.length)
        state.timer = setTimeout(tick, Number($("#speed").value));
      else togglePlayback(false);
    }
    state.timer = setTimeout(tick, Number($("#speed").value));
  }
}
function visibleNodes() {
  // Progressive rendering is bounded at 320 recorded nodes. All data remains downloadable.
  return state.trace?.nodes.slice(0, Math.min(state.visible, 320)) || [];
}
function updateTransform() {
  $("#tree-transform").setAttribute(
    "transform",
    `translate(${state.tx},${state.ty}) scale(${state.zoom})`,
  );
}
function fitTree() {
  const positions = [
    ...layoutTree(state.trace?.nodes.slice(0, 320) || []).values(),
  ];
  if (!positions.length) return;
  const xs = positions.map((p) => p.x),
    ys = positions.map((p) => p.y);
  const w = Math.max(...xs) - Math.min(...xs) + 110,
    h = Math.max(...ys) + 120;
  state.zoom = Math.min(1.25, 800 / w, 345 / h);
  state.tx = (900 - (Math.max(...xs) + Math.min(...xs)) * state.zoom) / 2;
  state.ty = (420 - (Math.max(...ys) + 25) * state.zoom) / 2;
  updateTransform();
}
function renderTree(fit = true) {
  const nodes = visibleNodes();
  const recordedLayout = layoutTree(state.trace?.nodes.slice(0, 320) || []);
  $("#tree-transform").innerHTML = treeMarkup(
    nodes,
    state.selected,
    recordedLayout,
  ).markup;
  $("#tree-empty").hidden = nodes.length > 0;
  $("#timeline").max = state.trace?.nodes.length || 1;
  $("#timeline").value = state.visible;
  $("#step-count").textContent =
    `${Math.max(0, state.visible - 1)} / ${Math.max(0, (state.trace?.nodes.length || 1) - 1)} steps`;
  $(".tree-watermark").textContent =
    state.visible > 320
      ? "FIRST 320 RECORDED STATES · EXPORT FULL TRACE FOR ALL ATTEMPTS"
      : "THE SPACE OF POSSIBLE PROOFS";
  if (fit) fitTree();
}
function showRankings(node) {
  const records = state.trace?.rankings || [];
  let ranking = records.find((r) => r.node_id === node.id);
  if (!ranking && node.parent !== null)
    ranking = records.find((r) => r.node_id === node.parent);
  $("#rankings-panel").hidden = !ranking;
  if (!ranking) return;
  $("#ranking-state").textContent = `STATE ${ranking.node_id}`;
  $("#ranking-note").textContent =
    `${state.trace.algorithm === "outcome" ? "Outcome scores determine candidate order; all features are available before candidate execution." : state.trace.algorithm === "learned" ? "Learned scores determine candidate order; the original heuristic orders frontier states." : "This run follows its original policy; learned scores are recorded annotations."} Larger scores rank first within each policy; the two score scales differ. Scores are not probabilities or proof certificates. ${ranking.node_id !== node.id ? "Showing the expanded parent of the selected node." : "Showing candidates generated from this exact Lean state."}`;
  const prefix = [];
  let ancestor = state.trace.nodes[ranking.node_id];
  while (ancestor?.parent !== null && ancestor?.parent !== undefined) {
    prefix.unshift(ancestor.tactic);
    ancestor = state.trace.nodes[ancestor.parent];
  }
  const key = continuationKey(state.trace.task.id, prefix);
  $("#open-continuations").hidden = !key;
  $("#open-continuations").onclick = () => {
    selectContinuation(key);
    showView("continuations");
  };
  const candidates = ranking.candidates;
  const hasOutcome = candidates.some((c) => Number.isFinite(c.outcome_score));
  $("#outcome-ranking-header").hidden = !hasOutcome;
  const outcomeOrder = [...candidates].sort(
    (a, b) =>
      b.outcome_score - a.outcome_score ||
      a.generated_order - b.generated_order,
  );
  const heuristic = [...candidates].sort(
    (a, b) =>
      b.heuristic_score - a.heuristic_score ||
      a.generated_order - b.generated_order,
  );
  const learned = [...candidates].sort(
    (a, b) =>
      b.learned_score - a.learned_score ||
      a.generated_order - b.generated_order,
  );
  $("#ranking-rows").innerHTML = candidates
    .map((c) => {
      const attempt = state.trace.nodes.find(
        (n) => n.parent === ranking.node_id && n.tactic === c.tactic,
      );
      const outcome = attempt
        ? attempt.id < state.visible
          ? attempt.status
          : "Not replayed yet"
        : "Not executed";
      const contributions = c.contributions
        .map(([name, value]) => `${name}: ${value.toFixed(6)}`)
        .join("\n");
      return `<tr><td>${c.actual_rank}</td><td><code>${esc(c.tactic)}</code><details><summary>Top feature contributions</summary><pre>${esc(contributions)}</pre></details></td><td>${heuristic.indexOf(c) + 1} / ${c.heuristic_score.toFixed(3)}</td><td>${learned.indexOf(c) + 1} / ${c.learned_score.toFixed(3)}</td>${hasOutcome ? `<td>${outcomeOrder.indexOf(c) + 1} / ${c.outcome_score.toFixed(6)}<details><summary>Phase 3 features</summary><pre>${esc(c.outcome_contributions.map(([name, value]) => `${name}: ${value.toFixed(6)}`).join("\n"))}</pre></details></td>` : ""}<td>${esc(outcome)}</td></tr>`;
    })
    .join("");
}
function inspect(id) {
  if (!state.trace) return;
  const node = state.trace.nodes.find((n) => n.id === id);
  if (!node) return;
  state.selected = id;
  showRankings(node);
  $("#node-label").textContent = `STATE ${String(id).padStart(2, "0")}`;
  $("#selected-tactic").textContent = node.tactic || "Initial goal";
  $("#selected-reason").textContent =
    node.reason +
    (node.provenance ? ` · ${node.provenance}` : "") +
    (node.status === "rejected"
      ? ". Rejected by Lean; parent state shown below."
      : node.status === "error"
        ? ". Interrupted attempt; parent state shown below."
        : "");
  const proofState =
    node.state || state.trace.nodes.find((n) => n.id === node.parent)?.state;
  const first = proofState?.goals[0];
  $("#hypotheses").textContent =
    first?.hypotheses.map((h) => `${h.name} : ${h.type.text}`).join("\n") ||
    "No local hypotheses";
  $("#goals").textContent = proofState?.goals.length
    ? proofState.goals.map((g) => `⊢ ${g.target.text}`).join("\n\n")
    : "✓ No remaining goals";
  $("#node-error").hidden = !node.error;
  $("#node-error").textContent = node.error || "";
  $$("#tree-svg .tree-node").forEach((el) =>
    el.classList.toggle("selected-node", Number(el.dataset.node) === id),
  );
}
function setTrace(trace) {
  togglePlayback(false);
  state.trace = trace;
  $("#rankings-panel").hidden = true;
  state.visible = trace?.nodes.length || 1;
  state.selected = 0;
  const m = trace?.metrics;
  $("#metric-states").textContent = m?.expanded_states ?? "—";
  $("#metric-attempts").textContent = m?.attempted_candidates ?? "—";
  $("#metric-depth").textContent = m?.max_depth ?? "—";
  $("#metric-time").textContent = m ? `${m.elapsed_s.toFixed(2)}s` : "—";
  const statusLabels = {
    verified: "✓ Verified",
    not_found_within_budget: "No proof found",
    execution_error: "Execution error",
    cancelled: "Cancelled",
    unsupported: "Unsupported",
  };
  $("#metric-status").textContent = trace
    ? statusLabels[trace.status]
    : "Awaiting trace";
  $("#metric-status-note").textContent =
    trace?.status === "verified"
      ? "Fresh Lean process + axiom audit"
      : trace?.termination || "Fresh Lean process + axiom audit";
  $("#proof-code").textContent =
    trace?.lean_source ||
    (trace
      ? `No verified proof found.\n${trace.termination}\nThis is not evidence that the theorem is false.`
      : "Choose a theorem and explore its proof search.");
  $("#proof-badge").textContent =
    trace?.status === "verified"
      ? "✓ KERNEL CHECKED"
      : trace
        ? "INCOMPLETE SEARCH"
        : "NO RESULT YET";
  $("#proof-method").textContent = trace
    ? `${trace.algorithm === "outcome" ? "Outcome-aware" : trace.algorithm === "learned" ? "Learned" : trace.algorithm === "bfs" ? "Breadth-first" : "Best-first"} · ${trace.proof.length} proof steps${trace.metadata.repeat !== undefined ? ` · repeat ${Number(trace.metadata.repeat) + 1} of ${trace.task.id.startsWith("p3_") ? 2 : 3}` : ""}`
    : "";
  renderTree();
  if (trace?.nodes.length) inspect(0);
  else {
    $("#tree-empty").textContent =
      "No recorded run for this task. Use live local search to compute one.";
    $("#hypotheses").textContent = "";
    $("#goals").textContent = "";
    $("#selected-tactic").textContent = "Initial goal";
    $("#selected-reason").textContent =
      "Choose a recorded run or compute a new local search.";
    $("#node-error").hidden = true;
  }
}
async function loadSelected() {
  notice();
  const selectedTask = state.task.id,
    algorithm = state.algorithm;
  try {
    const trace = await fetchTrace(selectedTask, algorithm);
    if (state.task.id === selectedTask && state.algorithm === algorithm)
      setTrace(trace);
  } catch (error) {
    notice(error.message);
  }
}
async function run() {
  if (state.job) {
    await fetch(`/api/jobs/${state.job}`, { method: "DELETE" });
    notice("Cancellation requested. Lean processes will be cleaned up.");
    return;
  }
  if (state.mode === "replay") {
    await loadSelected();
    if (state.trace) {
      state.visible = 1;
      renderTree();
      togglePlayback(true);
    } else
      notice(
        "This task has no recorded run. Start the local application for a new Lean search.",
      );
    return;
  }
  $("#run-label").textContent = "Starting Lean…";
  $("#run-button").disabled = true;
  notice(
    "Lean is exploring actual candidate tactics. The completed trace will be replayable here.",
  );
  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task_id: state.task.id,
        algorithm: state.algorithm,
      }),
    });
    if (!response.ok)
      throw new Error(
        (await response.json()).detail || "Search could not start.",
      );
    state.job = (await response.json()).job_id;
    $("#run-button").disabled = false;
    $("#run-label").textContent = "Cancel computation";
    const taskId = state.task.id;
    while (state.job) {
      await new Promise((resolve) => setTimeout(resolve, 300));
      const response = await fetch(`/api/jobs/${state.job}`);
      if (!response.ok)
        throw new Error("Search session could not be retrieved.");
      const job = await response.json();
      if (job.state === "running") continue;
      if (job.trace && state.task.id === taskId) {
        setTrace(job.trace);
        notice(
          `New computation completed: ${job.trace.status}. Replay shows the actual recorded attempts.`,
        );
      } else
        notice(
          job.error ||
            "Search completed. Reselect the original theorem to run it again.",
        );
      state.job = null;
    }
  } catch (error) {
    notice(error.message);
    state.job = null;
  } finally {
    $("#run-label").textContent = "Explore proof";
    $("#run-button").disabled = false;
  }
}
function miniTree(trace) {
  const nodes = trace.nodes.slice(0, 220),
    positions = [...layoutTree(nodes).values()];
  const w = Math.max(1, ...positions.map((p) => p.x)) + 100,
    h = Math.max(1, ...positions.map((p) => p.y)) + 130;
  return `<div class="tree-container"><svg viewBox="-50 -50 ${w} ${h}" role="img" aria-label="${esc(trace.algorithm)} recorded search tree">${treeMarkup(nodes, -1).markup}</svg></div>`;
}
async function compare() {
  $("#comparison-grid").textContent = "Loading recorded comparisons…";
  try {
    const traces = await Promise.all(
      ($("#compare-task").value.startsWith("p3_")
        ? ["bfs", "best_first", "learned", "outcome", "automation"]
        : $("#compare-task").value.startsWith("p2_")
          ? ["bfs", "best_first", "learned"]
          : ["bfs", "best_first"]
      ).map((algorithm) => fetchTrace($("#compare-task").value, algorithm)),
    );
    $("#comparison-grid").innerHTML = traces
      .map((trace, i) =>
        trace
          ? `<article class="card"><div class="card-top"><h2>${["Systematic breadth-first", "Heuristic best-first", "Learned candidate ranking", "Outcome-aware ranking", "Native Aesop reference"][i]}</h2><span class="subtle-pill">${trace.verification.verified ? "✓ VERIFIED" : "INCOMPLETE"}</span></div>${miniTree(trace)}<div class="comparison-metrics"><div><strong>${trace.metrics.expanded_states}</strong>expanded states</div><div><strong>${trace.metrics.attempted_candidates}</strong>tactic attempts</div><div><strong>${trace.metrics.elapsed_s.toFixed(2)}s</strong>wall time</div><div><strong>${trace.metrics.lean_execution_s.toFixed(3)}s</strong>Lean interaction</div></div><pre>${esc(trace.proof.length ? trace.proof.join("\n") : trace.termination)}</pre></article>`
          : `<article class="card benchmark-chart">No recorded ${["breadth-first", "best-first", "learned", "outcome", "native Aesop"][i]} run for this task.</article>`,
      )
      .join("");
  } catch (error) {
    $("#comparison-grid").textContent = error.message;
  }
}
function benchmarks() {
  if (!summaryData) {
    $("#benchmark-content").textContent =
      "No benchmark results recorded yet. Run the reproducible benchmark command to produce measurements.";
    return;
  }
  const groups = Object.entries(summaryData.results),
    p = summaryData.provenance;
  const names = {
    bfs: "Breadth-first",
    best_first: "Best-first",
    automation: "Native Aesop",
    learned: "Learned ranker (Phase 2)",
    outcome: "Outcome-aware (Phase 3)",
    applicability_only: "Ablation: applicability only",
    old_features_outcome: "Ablation: old features + outcomes",
  };
  $("#benchmark-content").innerHTML =
    `<div class="benchmark-cards"><article class="card"><div class="small-label">MATHEMATICAL TASKS</div><strong>${state.tasks.length}</strong><p>Logic · orders · algebra · sets</p></article><article class="card"><div class="small-label">RECORDED RUNS</div><strong>${groups.reduce((n, [, g]) => n + g.attempted, 0)}</strong><p>Including incomplete searches and errors</p></article><article class="card"><div class="small-label">HELD-OUT TASKS</div><strong>${state.tasks.filter((t) => t.split === "held_out").length}</strong><p>Split fixed before the comparative experiment</p></article></div><section class="card benchmark-chart"><h2>Independently verified proofs</h2>${groups.map(([key, g]) => `<div class="chart-row"><span>${names[key]}</span><div class="chart-bar"><span style="width:${g.success_rate * 100}%"></span></div><span>${g.verified} / ${g.attempted}${g.success_interval ? ` · 95% CI ${(100 * g.success_interval.lower).toFixed(1)}–${(100 * g.success_interval.upper).toFixed(1)}%` : ""}</span></div>`).join("")}<p class="method-note">Native Aesop is a separate Mathlib automation reference. Its results are not attributed to ProofLab search.</p></section><div class="card benchmark-table"><table><thead><tr><th>STRATEGY</th><th>VERIFIED</th><th>MEDIAN WALL TIME</th><th>LEAN INTERACTION</th><th>MEAN ATTEMPTS</th><th>MEAN EXPANSIONS</th><th>RESOURCE LIMITS</th><th>EXECUTION ERRORS</th></tr></thead><tbody>${groups.map(([key, g]) => `<tr><td>${names[key]}</td><td>${g.verified}/${g.attempted}</td><td>${g.median_wall_s.toFixed(2)}s</td><td>${g.mean_lean_execution_s.toFixed(3)}s</td><td>${g.mean_candidates.toFixed(2)}</td><td>${g.mean_expansions.toFixed(1)}</td><td>${g.resource_limits}</td><td>${g.execution_errors}</td></tr>`).join("")}</tbody></table></div><div class="card provenance"><div class="small-label">EXPERIMENT PROVENANCE</div>Model: ${esc(p.models?.outcome || p.model_sha256 || "Phase 1 handcrafted policies")}<br>Code: ${esc(p.code_commit)}<br>Lean: ${esc(p.lean_version)}<br>Mathlib: ${esc(p.mathlib_revision)}<br>Dataset SHA-256: ${esc(p.evaluation_sha256 || p.dataset_sha256)}<br>Host: ${esc(p.platform)}<br>Budget: ${esc(JSON.stringify(p.budget))}<br>${esc(p.timing_note)}<br>${summaryData.paired_differences ? `${p.repetitions === 2 ? "Two repeats per theorem for primary policies; one per ablation" : "Three repeats per theorem"}; 95% intervals resample theorem clusters. ${p.models ? "Outcome model" : "Learned"} minus handcrafted: success ${(100 * summaryData.paired_differences.best_first.success_rate.estimate).toFixed(1)} percentage points; attempts ${summaryData.paired_differences.best_first.attempted_candidates.estimate.toFixed(2)} per theorem. Failures remain in these means. Training loss does not establish a search improvement.` : "These descriptive results are not a claim of statistical significance."}</div>`;
}
function showView(view) {
  $$(".view").forEach((el) => (el.hidden = el.id !== `${view}-view`));
  $$("[data-view]").forEach((el) =>
    el.classList.toggle("active", el.dataset.view === view),
  );
  $("#crumb").textContent = {
    lab: "Proof explorer",
    compare: "Compare strategies",
    benchmarks: "Benchmarks",
    about: "Inside the lab",
    continuations: "Alternative continuations",
  }[view];
  if (view === "continuations") openContinuations();
  if (view === "compare") compare();
  if (view === "benchmarks") benchmarks();
  location.hash = view;
}

$$("[data-view]").forEach((el) =>
  el.addEventListener("click", () => showView(el.dataset.view)),
);
$$("[data-algorithm]").forEach((el) =>
  el.addEventListener("click", () => {
    setAlgorithm(el.dataset.algorithm);
    loadSelected();
  }),
);
$("#task-select").addEventListener("change", () => {
  showTheorem(state.tasks.find((t) => t.id === $("#task-select").value));
  loadSelected();
});
$("#run-button").addEventListener("click", run);
$("#play-toggle").addEventListener("click", () => togglePlayback());
$("#step-button").addEventListener("click", () => {
  togglePlayback(false);
  if (state.trace) {
    state.visible = Math.min(state.visible + 1, state.trace.nodes.length);
    renderTree(false);
    inspect(state.trace.nodes[state.visible - 1].id);
  }
});
$("#timeline").addEventListener("input", () => {
  togglePlayback(false);
  state.visible = Number($("#timeline").value);
  renderTree(false);
  inspect(state.trace.nodes[state.visible - 1].id);
});
$("#speed").addEventListener("change", () => {
  if (state.playing) togglePlayback(true);
});
$("#fit-tree").addEventListener("click", fitTree);
$("#zoom-in").addEventListener("click", () => {
  state.zoom *= 1.25;
  updateTransform();
});
$("#zoom-out").addEventListener("click", () => {
  state.zoom /= 1.25;
  updateTransform();
});
$("#tree-svg").addEventListener("click", (e) => {
  const n = e.target.closest("[data-node]");
  if (n) inspect(Number(n.dataset.node));
});
$("#tree-svg").addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    const n = e.target.closest("[data-node]");
    if (n) {
      e.preventDefault();
      inspect(Number(n.dataset.node));
    }
  }
});
let dragging = null;
$("#tree-svg").addEventListener("pointerdown", (e) => {
  if (!e.target.closest("[data-node]")) {
    dragging = { x: e.clientX, y: e.clientY, tx: state.tx, ty: state.ty };
    e.target.setPointerCapture(e.pointerId);
  }
});
$("#tree-svg").addEventListener("pointermove", (e) => {
  if (dragging) {
    const ratio = 900 / $("#tree-svg").clientWidth;
    state.tx = dragging.tx + (e.clientX - dragging.x) * ratio;
    state.ty = dragging.ty + (e.clientY - dragging.y) * ratio;
    updateTransform();
  }
});
$("#tree-svg").addEventListener("pointerup", () => (dragging = null));
$("#tree-svg").addEventListener("pointercancel", () => (dragging = null));
$("#tree-svg").addEventListener(
  "wheel",
  (e) => {
    e.preventDefault();
    state.zoom = Math.max(
      0.03,
      Math.min(6, state.zoom * (e.deltaY < 0 ? 1.1 : 0.9)),
    );
    updateTransform();
  },
  { passive: false },
);
$("#export-svg").addEventListener("click", () => {
  if (!state.trace) return;
  const svg = $("#tree-svg").cloneNode(true);
  svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  const style = document.createElementNS("http://www.w3.org/2000/svg", "style");
  style.textContent =
    ".tree-edge{fill:none;stroke:#658d79;stroke-width:1.5}.proof-edge{stroke:#34704a;stroke-width:3}.tree-node circle{fill:#eef5e9;stroke:#58834c}.tree-node text{fill:#183d2a;font:10px monospace}.node-symbol{font-size:14px!important}.rejected circle{stroke:#b17b6c;fill:#f8eee9}.on-path circle{fill:#bde6a8}";
  svg.prepend(style);
  download(`${state.task.id}-search.svg`, svg.outerHTML, "image/svg+xml");
});
$("#export-trace").addEventListener("click", () => {
  if (state.trace)
    download(
      `${state.task.id}-${state.algorithm}.json`,
      JSON.stringify(state.trace, null, 2),
      "application/json",
    );
});
$("#copy-proof").addEventListener("click", async () => {
  if (state.trace?.lean_source) {
    try {
      await navigator.clipboard.writeText(state.trace.lean_source);
      $("#copy-proof").textContent = "Copied ✓";
      setTimeout(() => ($("#copy-proof").textContent = "Copy"), 1800);
    } catch {
      notice("Clipboard unavailable. Download the Lean artifact instead.");
    }
  }
});
$("#download-proof").addEventListener("click", () => {
  if (state.trace?.lean_source)
    download(`${state.task.id}.lean`, state.trace.lean_source);
});
$("#compare-run").addEventListener("click", compare);
$("#compare-task").addEventListener("change", compare);
$("#theme-toggle").addEventListener("click", () => {
  const theme =
    document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("prooflab-theme", theme);
});
$("#mode-toggle").addEventListener("click", () => {
  state.mode = state.mode === "live" ? "replay" : "live";
  $("#mode-badge").textContent =
    state.mode === "live" ? "Live local search" : "Recorded replay";
  $("#mode-toggle").textContent =
    state.mode === "live" ? "Use recorded traces" : "Use live search";
  notice(
    state.mode === "live"
      ? "New searches run Lean locally. Only repository-owned theorem statements can be executed."
      : "Playback uses authentic traces from recorded Lean computations.",
  );
});
document.addEventListener("keydown", (e) => {
  if (
    e.code === "Space" &&
    !["INPUT", "SELECT", "BUTTON", "TEXTAREA"].includes(
      document.activeElement.tagName,
    )
  ) {
    e.preventDefault();
    togglePlayback();
  }
});

async function chooseDataset(name) {
  const data = datasets[name];
  if (!data) {
    notice("This dataset has no exported executions yet.");
    return;
  }
  togglePlayback(false);
  state.dataset = name;
  state.repeat = 0;
  const reps = name === "phase3" ? 2 : 3;
  $("#repeat-select").innerHTML = Array.from(
    { length: reps },
    (_, i) => `<option value="${i}">${i + 1} of ${reps}</option>`,
  ).join("");
  $("#repeat-label").hidden = name === "phase1";
  if (name === "phase1") {
    state.repeat = 0;
    $("#repeat-select").value = "0";
  }
  state.tasks = data.tasks;
  state.manifest = data.manifest;
  summaryData = data.summary;
  const options = state.tasks
    .map(
      (t) =>
        `<option value="${esc(t.id)}">${esc(t.title)} · ${esc(t.domain)}</option>`,
    )
    .join("");
  $("#task-select").innerHTML = options;
  $("#compare-task").innerHTML = options;
  showTheorem(state.tasks[0]);
  await loadSelected();
  if (!$("#compare-view").hidden) compare();
  if (!$("#benchmarks-view").hidden) benchmarks();
}
$("#dataset-select").addEventListener("change", () =>
  chooseDataset($("#dataset-select").value),
);

$("#repeat-select").addEventListener("change", () => {
  state.repeat = Number($("#repeat-select").value);
  loadSelected();
  if (!$("#compare-view").hidden) compare();
});

async function boot() {
  document.documentElement.dataset.theme =
    localStorage.getItem("prooflab-theme") || "light";
  const results = await Promise.all([
    fetch(`${base}tasks.json`),
    fetch(`${base}traces/manifest.json`),
    fetch(`${base}summary.json`),
  ]);
  if (!results[0].ok)
    throw new Error(
      "Benchmark dataset is missing. Run scripts/export_demo.py and rebuild.",
    );
  state.tasks = await results[0].json();
  state.manifest = results[1].ok ? await results[1].json() : [];
  summaryData = results[2].ok ? await results[2].json() : null;
  datasets.phase1 = {
    tasks: state.tasks,
    manifest: state.manifest,
    summary: summaryData,
  };
  const phase2 = await Promise.all(
    ["tasks.json", "manifest.json", "summary.json"].map(async (file) => {
      const response = await fetch(`${base}phase2/${file}`);
      return response.ok ? response.json() : null;
    }),
  );
  if (phase2[0])
    datasets.phase2 = {
      tasks: phase2[0],
      manifest: phase2[1] || [],
      summary: phase2[2],
    };
  const phase3 = await Promise.all(
    ["tasks.json", "manifest.json", "summary.json"].map(async (file) => {
      const response = await fetch(`${base}phase3/${file}`);
      return response.ok ? response.json() : null;
    }),
  );
  if (phase3[0])
    datasets.phase3 = {
      tasks: phase3[0],
      manifest: phase3[1] || [],
      summary: phase3[2],
    };
  await initializeContinuations(base);
  await chooseDataset("phase1");
  const view = location.hash.slice(1);
  if (["lab", "compare", "benchmarks", "about", "continuations"].includes(view))
    showView(view);
  if (["localhost", "127.0.0.1"].includes(location.hostname)) {
    try {
      const r = await fetch("/api/health");
      if (r.ok && (await r.json()).service === "prooflab")
        $("#mode-toggle").hidden = false;
    } catch {
      /* Static replay needs no backend. */
    }
  }
}
boot().catch((error) => {
  notice(error.message);
  $("#tree-empty").textContent = "No computation results available yet.";
});
