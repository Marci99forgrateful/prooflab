import { escapeHtml as esc } from "./tree.js";

export function adaptiveEvidence(query, trace, nodeId) {
  if (query.phase !== 6) return "";
  const allocation = query.allocation || {};
  const attempts = trace.nodes.filter((n) => n.parent === nodeId);
  const predicted = Object.entries(query.predicted_log_costs || {});
  return `<section class="adaptive-decision" aria-label="Adaptive Proof Search Explorer">
    <h4>Adaptive Proof Search Explorer</h4>
    <p><strong>${esc(query.decision)}</strong> strategy · expansion ${query.stage} · ${esc(query.mode)} policy</p>
    <div class="adaptive-facts"><span>Recognized structures<br/><strong>${esc(query.recognized_structures?.join(", ") || "No indexed typeclass")}</strong></span><span>Symbolic / novelty slots used<br/><strong>${allocation.baseline ?? "—"} / ${allocation.novelty ?? "—"}</strong> of ${allocation.cap ?? trace.budget.max_candidates}</span><span>Actual attempts at this state<br/><strong>${attempts.length}</strong> · ${attempts.filter((n) => ["accepted", "solved"].includes(n.status)).length} accepted</span></div>
    ${predicted.length ? `<details><summary>Learned strategy decision · conditional cost estimates</summary><table><thead><tr><th>Mode</th><th>Predicted log(1 + attempts)</th></tr></thead><tbody>${predicted.map(([mode, value]) => `<tr><td>${esc(mode)}</td><td>${value.toFixed(5)}</td></tr>`).join("")}</tbody></table><p class="method-note">The smallest predicted conditional cost chooses the strategy. Training excludes unresolved/censored modes as cost targets, so these estimates have success-conditioned selection bias. They do not estimate proof probability or certify usefulness.</p></details>` : `<p class="method-note">Deterministic mathematical-context decision; no fitted selector was used.</p>`}
    <p class="method-note">${esc(query.scheduling)}. Retrieval selects availability; it cannot change execution ties for an identical pool. Novelty relevance is consumed in hybrid mode; typed mode retains its recorded deterministic typed allocation.</p>
    <details><summary>Allocation and staged decisions</summary><p class="method-note">${esc(JSON.stringify(allocation))}. ${query.mode === "staged" ? "The first two non-existential expansions use symbolic proposals; later expansions use the context gate. Existential roots retrieve immediately." : "One continuous search within one shared global budget."} No restarted search or extra fallback budget.</p><p class="method-note">${query.potential_complete ? "The potential native proposal universe was queried and retained." : "No native retrieval was requested at this state. Unqueried typed availability and relevance remain unknown."}</p><p class="method-note">Model ${esc(query.model_sha256 || "not used")}.</p></details>
  </section>`;
}
