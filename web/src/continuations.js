import { escapeHtml as esc, layoutTree, treeMarkup } from "./tree.js";

const $ = (s) => document.querySelector(s);
let entries = [],
  current = null,
  selected = null,
  base = "";
let generation = 0;

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
export function classifyContinuation(o) {
  if (o.status !== "accepted")
    return { name: "Lean rejected in this state", kind: "invalid" };
  if (!o.continuation)
    return { name: "Valid · continuation unexplored", kind: "unexplored" };
  if (
    o.continuation.status === "verified" &&
    o.continuation.verification.verified
  )
    return { name: "Valid · verified completion", kind: "verified" };
  if (o.continuation.status === "execution_error")
    return { name: "Valid · execution error", kind: "censored" };
  return { name: "Valid · bounded unresolved", kind: "censored" };
}
function tree(nodes) {
  const visible = nodes.slice(0, 180),
    positions = [...layoutTree(visible).values()];
  const w = Math.max(1, ...positions.map((p) => p.x)) + 100,
    h = Math.max(1, ...positions.map((p) => p.y)) + 130;
  return `<div class="tree-container continuation-tree"><svg viewBox="-50 -50 ${w} ${h}" role="img" aria-label="Actual continuation search tree">${treeMarkup(visible, -1).markup}</svg></div>${nodes.length > 180 ? "<p>First 180 nodes shown; export contains every actual attempt.</p>" : ""}`;
}
function renderBranch(target, index) {
  const o = selected.observations[index],
    c = o.continuation,
    label = classifyContinuation(o);
  $(target).innerHTML =
    `<div class="card-top"><h2><code>${esc(o.candidate.tactic)}</code></h2><span class="continuation-badge ${label.kind}">${esc(label.name)}</span></div>`;
  if (!c) {
    $(target).insertAdjacentHTML(
      "beforeend",
      `<p class="method-note">${o.status === "accepted" ? "Lean accepted this action. Its downstream search was not executed; no completion claim is made." : "This particular application was rejected by Lean. This does not classify the tactic as mathematically incorrect."}</p>${o.error ? `<pre class="continuation-code">${esc(o.error)}</pre>` : ""}`,
    );
    return;
  }
  const m = c.metrics;
  $(target).insertAdjacentHTML(
    "beforeend",
    `${tree(c.nodes)}<div class="comparison-metrics"><div><strong>${m.attempted_candidates}</strong>attempts incl. first action</div><div><strong>${m.expanded_states}</strong>downstream expansions</div><div><strong>${m.search_s.toFixed(3)}s</strong>search time</div><div><strong>${m.verification_s.toFixed(3)}s</strong>fresh audit time</div></div><p class="method-note">${esc(c.termination)} · Root is the actual state after the selected action. ${c.status === "verified" ? "Full proof below includes the replayed prefix; fresh audit passed." : "No verified completion found within this finite search. This is not evidence of impossibility."}</p><pre class="continuation-code">${esc(c.proof.length ? c.proof.join("\n") : "No independently verified completed proof.")}</pre>${c.verification.verified ? `<p class="method-note">Audited axioms: ${esc(c.verification.axioms.join(", ") || "none")}</p>` : ""}`,
  );
  $(target).insertAdjacentHTML(
    "beforeend",
    '<details class="branch-inspector"><summary class="continuation-node-label"></summary><pre class="continuation-code continuation-node-state"></pre></details>',
  );
  function inspectNode(id, expand = false) {
    const node = c.nodes.find((n) => n.id === id);
    if (!node) return;
    const proofState =
      node.state || c.nodes.find((n) => n.id === node.parent)?.state;
    const label = $(target).querySelector(".continuation-node-label");
    label.textContent = `Actual state ${id} · ${node.tactic || "after first accepted action"}${node.state ? "" : " · parent context for rejected/interrupted step"}`;
    const context =
      proofState?.goals[0]?.hypotheses
        .map((h) => `${h.name} : ${h.type.text}`)
        .join("\n") || "";
    const goals = proofState?.goals.length
      ? proofState.goals.map((g) => `⊢ ${g.target.text}`).join("\n\n")
      : "No remaining goals in this native state";
    $(target).querySelector(".continuation-node-state").textContent =
      `${context}\n\n${goals}${node.error ? "\n\n" + node.error : ""}`;
    $(target)
      .querySelectorAll(".tree-node")
      .forEach((el) =>
        el.classList.toggle("selected-node", Number(el.dataset.node) === id),
      );
    if (expand) $(target).querySelector(".branch-inspector").open = true;
  }
  $(target)
    .querySelectorAll(".tree-node")
    .forEach((node) => {
      const hit = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "rect",
      );
      for (const [name, value] of Object.entries({
        x: "-50",
        y: "-24",
        width: "100",
        height: "75",
        fill: "transparent",
        stroke: "none",
      }))
        hit.setAttribute(name, value);
      node.insertBefore(hit, node.firstChild);

      node.addEventListener("click", () =>
        inspectNode(Number(node.dataset.node), true),
      );
      node.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          inspectNode(Number(node.dataset.node), true);
        }
      });
    });
  const viewport = $(target).querySelector(".continuation-tree");
  const svg = viewport.querySelector("svg");
  const full = svg.viewBox.baseVal;
  const fit = { x: full.x, y: full.y, width: full.width, height: full.height };
  function setBox(box) {
    svg.setAttribute("viewBox", `${box.x} ${box.y} ${box.width} ${box.height}`);
  }
  viewport.insertAdjacentHTML(
    "beforeend",
    '<div class="continuation-zoom"><button data-czoom="in" aria-label="Zoom in continuation">+</button><button data-czoom="out" aria-label="Zoom out continuation">−</button><button data-czoom="fit">Fit all</button></div>',
  );
  viewport.querySelectorAll("[data-czoom]").forEach((button) =>
    button.addEventListener("click", () => {
      if (button.dataset.czoom === "fit") {
        setBox(fit);
        return;
      }
      const box = svg.viewBox.baseVal,
        factor = button.dataset.czoom === "in" ? 0.7 : 1 / 0.7;
      const width = box.width * factor,
        height = box.height * factor;
      setBox({
        x: box.x + (box.width - width) / 2,
        y: box.y + (box.height - height) / 2,
        width,
        height,
      });
    }),
  );
  let drag = null;
  svg.addEventListener("pointerdown", (event) => {
    if (event.target.closest(".tree-node")) return;
    const box = svg.viewBox.baseVal;
    drag = {
      x: event.clientX,
      y: event.clientY,
      box: { x: box.x, y: box.y, width: box.width, height: box.height },
    };
    svg.setPointerCapture(event.pointerId);
  });
  svg.addEventListener("pointermove", (event) => {
    if (drag) {
      const scale = drag.box.width / svg.clientWidth;
      setBox({
        ...drag.box,
        x: drag.box.x - (event.clientX - drag.x) * scale,
        y: drag.box.y - (event.clientY - drag.y) * scale,
      });
    }
  });
  svg.addEventListener("pointerup", () => (drag = null));
  svg.addEventListener("pointercancel", () => (drag = null));
  if (fit.width > 1000 && svg.clientWidth) {
    const root = layoutTree(c.nodes.slice(0, 180)).get(c.nodes[0].id);
    const width = 800,
      height = (width * svg.clientHeight) / svg.clientWidth;
    setBox({ x: root.x - width / 2, y: -50, width, height });
  }
  inspectNode(0);
}
function renderState() {
  const entry = entries.find(
    (e) => e.key === $("#continuation-state-select").value,
  );
  if (!entry || !current) return;
  selected = current.record.states.find((s) => s.depth === entry.depth);
  const annotations = current.annotations[String(selected.depth)],
    goal = selected.state.goals[0];
  $("#continuation-role").textContent =
    entry.role === "development"
      ? "Development evidence used for training"
      : "Held-out diagnostic after model freeze · never training data";
  const baselineNames = {
    learned: "Phase 2",
    applicability_only: "the applicability-only ablation",
    bfs: "BFS",
  };
  $("#continuation-case").textContent = entry.case
    ? `${entry.case.kind === "different_verified_path" ? "Different verified paths" : entry.case.attempt_delta < 0 ? "A measured local benefit" : "A measured local regression"}: Phase 3 used ${Math.abs(entry.case.attempt_delta)} ${entry.case.attempt_delta < 0 ? "fewer" : "more"} attempts than ${baselineNames[entry.case.baseline] || entry.case.baseline} in the main experiment. The diagnostic rollouts below are separate recorded searches, not new training labels or an aggregate improvement claim.`
    : "The alternatives below are actual development evidence. This view is not a held-out performance claim.";
  $("#continuation-provenance").textContent =
    `Source SHA-256 ${current.source_sha256}. The two scores use this pre-action state only. Successor changes below are observed Lean outcomes, not inputs supplied to the deployed model.`;
  $("#continuation-context").textContent =
    goal.hypotheses.map((h) => `${h.name} : ${h.type.text}`).join("\n") +
    "\n\n" +
    selected.state.goals.map((g) => `⊢ ${g.target.text}`).join("\n");
  $("#continuation-prefix").textContent =
    selected.prefix.join("\n") || "(Initial theorem state; no prefix)";
  $("#continuation-rows").innerHTML = selected.observations
    .map((o, i) => {
      const a = annotations.find((a) => a.tactic === o.candidate.tactic),
        label = classifyContinuation(o);
      const before = selected.state.goals.length,
        after = o.successor?.goals.length;
      const products = a.outcome_contributions
        .map(([n, v]) => `${n}: ${v.toFixed(6)}`)
        .join("\n");
      return `<tr><td><button class="text-button" data-continuation="${i}"><code>${esc(o.candidate.tactic)}</code></button><details><summary>Outcome model features</summary><pre>${esc(products)}</pre></details></td><td><span class="continuation-badge ${label.kind}">${esc(label.name)}</span></td><td>${a.phase2_rank} / ${a.phase2_score.toFixed(3)}</td><td>${a.outcome_rank} / ${a.outcome_score.toFixed(6)}</td><td>${after === undefined ? "—" : `${before} → ${after} goals`}</td><td>${o.continuation?.verification.verified ? o.continuation.metrics.attempted_candidates : "—"}</td></tr>`;
    })
    .join("");
  const options = selected.observations
    .map(
      (o, i) =>
        `<option value="${i}">${esc(o.candidate.tactic)} · ${esc(classifyContinuation(o).name)}</option>`,
    )
    .join("");
  $("#continuation-left-select").innerHTML = options;
  $("#continuation-right-select").innerHTML = options;
  const successful = selected.observations
    .map((o, i) => ({ o, i }))
    .filter((x) => x.o.continuation?.verification.verified)
    .sort(
      (a, b) =>
        a.o.continuation.metrics.attempted_candidates -
        b.o.continuation.metrics.attempted_candidates,
    );
  const explored = selected.observations
    .map((o, i) => ({ o, i }))
    .filter((x) => x.o.continuation);
  const left = successful[0]?.i ?? explored[0]?.i ?? 0;
  let right = successful.at(-1)?.i ?? explored.at(-1)?.i ?? left;
  if (right === left)
    right = explored.find((item) => item.i !== left)?.i ?? left;
  $("#continuation-left-select").value = String(left);
  $("#continuation-right-select").value = String(right);
  renderBranch("#continuation-left", left);
  renderBranch("#continuation-right", right);
  $("#continuation-rows")
    .querySelectorAll("[data-continuation]")
    .forEach((button) =>
      button.addEventListener("click", () => {
        $("#continuation-left-select").value = button.dataset.continuation;
        renderBranch("#continuation-left", Number(button.dataset.continuation));
      }),
    );
}
async function loadState() {
  const entry = entries.find(
    (e) => e.key === $("#continuation-state-select").value,
  );
  if (!entry) return;
  const version = ++generation;
  $("#continuation-status").textContent =
    "Loading actual recorded continuations…";
  try {
    const response = await fetch(base + entry.url);
    if (!response.ok)
      throw new Error("The actual continuation record could not be loaded.");
    const data = await response.json();
    if (version !== generation) return;
    current = data;
    renderState();
    $("#continuation-status").textContent = "";
  } catch (error) {
    $("#continuation-status").textContent = error.message;
  }
}
export async function initializeContinuations(assetBase) {
  base = assetBase;
  const response = await fetch(`${base}phase3/continuations.json`);
  if (!response.ok) return;
  entries = await response.json();
  $("#continuation-state-select").innerHTML = entries
    .map(
      (e) =>
        `<option value="${esc(e.key)}">${e.role === "diagnostic" ? `Evaluation diagnostic${e.case ? " · " + e.case.kind.replaceAll("_", " ") : ""}` : "Development"} · ${esc(e.title)} · depth ${e.depth} · ${e.verified}/${e.explored} verified</option>`,
    )
    .join("");
  $("#continuation-state-select").addEventListener("change", loadState);
  $("#continuation-left-select").addEventListener("change", () =>
    renderBranch(
      "#continuation-left",
      Number($("#continuation-left-select").value),
    ),
  );
  $("#continuation-right-select").addEventListener("change", () =>
    renderBranch(
      "#continuation-right",
      Number($("#continuation-right-select").value),
    ),
  );
  $("#export-continuations").addEventListener("click", () => {
    if (current)
      download(`${current.record.task_id}-actual-continuations.json`, current);
  });
}
export function continuationKey(taskId, prefix) {
  return entries.find(
    (e) =>
      e.task_id === taskId &&
      JSON.stringify(e.prefix) === JSON.stringify(prefix),
  )?.key;
}
export function selectContinuation(key) {
  if (!entries.some((e) => e.key === key)) return;
  $("#continuation-state-select").value = key;
  loadState();
}

export function openContinuations() {
  if (!current && generation === 0 && entries.length) loadState();
}
