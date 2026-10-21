import { escapeHtml as esc } from "./tree.js";
import { adaptiveEvidence } from "./adaptive.js";

const number = (v, digits = 4) =>
  typeof v === "number" ? v.toFixed(digits) : "—";

export function candidateEvidence(trace, nodeId, row) {
  const tactic = row.tactic || row.candidate?.tactic;
  const node = trace.nodes.find(
    (n) => n.parent === nodeId && n.tactic === tactic,
  );
  if (!node) return "Unexplored in this execution · outcome unknown";
  if (node.on_proof_path && trace.verification.verified)
    return "On independently verified complete proof path";
  if (node.status === "accepted")
    return "Lean accepted · downstream outcome unknown";
  if (node.status === "rejected")
    return `Lean rejected: ${node.error || "application failed"}`;
  return `${node.status}: ${node.error || ""}`;
}

export function retrievalRows(trace, nodeId, declarations = []) {
  const query = trace.retrievals?.find((r) => r.node_id === nodeId);
  if (!query) return { query: null, rows: [] };
  const types = new Map(declarations.map((r) => [r.name, r]));
  const scored = new Map(
    (query.pool || []).map((r) => [r.candidate.tactic, r]),
  );
  const all = new Map(
    (query.native?.rows || [])
      .filter((r) => r.tactic)
      .map((r) => [r.tactic, r]),
  );
  for (const [tactic, row] of scored)
    all.set(tactic, { ...all.get(tactic), ...row });
  for (const tactic of query.original || [])
    if (!all.has(tactic)) all.set(tactic, { tactic, family: "original" });
  const ranks = new Map(
    (trace.rankings?.find((r) => r.node_id === nodeId)?.candidates || []).map(
      (c) => [c.tactic, c],
    ),
  );
  const rows = [...all.values()].map((row) => {
    const tactic = row.tactic || row.candidate?.tactic;
    return {
      ...types.get(row.declaration),
      ...row,
      tactic,
      selected: query.selected.includes(tactic),
      actual_rank: ranks.get(tactic)?.actual_rank,
      heuristic_score:
        ranks.get(tactic)?.heuristic_score ?? row.candidate?.prior,
      p3_score: ranks.get(tactic)?.outcome_score,
      evidence: candidateEvidence(trace, nodeId, row),
    };
  });
  const eligible = rows.filter(
    (r) => r.compatible === true && !r.protected && r.family !== "original",
  );
  for (const row of rows) {
    if (!eligible.includes(row)) continue;
    row.deterministic_rank =
      typeof row.deterministic_score === "number"
        ? 1 +
          eligible.filter(
            (r) => r.deterministic_score > row.deterministic_score,
          ).length
        : null;
    row.learned_rank =
      typeof row.learned_score === "number"
        ? 1 + eligible.filter((r) => r.learned_score > row.learned_score).length
        : null;
  }
  return { query, rows };
}

export function renderPremises(container, trace, nodeId, declarations = []) {
  const { query, rows } = retrievalRows(trace, nodeId, declarations);
  if (!query) {
    container.innerHTML =
      '<p class="method-note">No native retrieval query was executed at this state. Its exact goals remain above. Unexpanded states and opaque external references have no invented candidate rankings.</p>';
    return;
  }
  const native = query.native;
  const sourceUrl = (module) => {
    if (!module || module === "current environment") return null;
    const path = module.replaceAll(".", "/") + ".lean";
    return module.startsWith("Mathlib.")
      ? `https://github.com/leanprover-community/mathlib4/blob/f897ebcf72cd16f89ab4577d0c826cd14afaafc7/${path}`
      : /^(Init|Lean|Std)(\.|$)/.test(module)
        ? `https://github.com/leanprover/lean4/blob/797c613eb9b6d4ec95db23e3e00af9ac6657f24b/src/${path}`
        : null;
  };
  container.innerHTML = `${adaptiveEvidence(query, trace, nodeId)}<p class="method-note"><strong>${esc(query.mode)}</strong> · ${query.selected.length}/${trace.budget.max_candidates} selected · ${query.displaced?.length || 0} original actions displaced · query ${number(query.query_wall_s)}s${native ? ` · ${native.declaration_probes} declaration probes · ${native.rewrite_probes} rewrite directions · ${native.term_constructions} term constructions · ${native.heartbeats} allocation heartbeats` : " · original/expanded generator has no native query"}.</p>
    <p class="method-note">Compatibility proposes an action; acceptance and complete-proof verification are separate evidence.</p>
    <details class="premise-method"><summary>Selection policy, model and score interpretation</summary>
    <p class="method-note">${esc(typeof query.allocation === "object" ? JSON.stringify(query.allocation) : query.allocation || "Original fixed-cap generation")}. Native compatibility checks potential unification/instances; actual application and verified usefulness are separate observations. A larger retrieval score chooses a novelty slot; score ranks below cover compatible non-protected proposals, with ties sharing rank; the displayed actual rank comes from the separate action scheduler. ${query.phase === 6 ? "Phase 6 equal downstream scores use explicit tactic-string ties, independent of retrieval input order." : "Historical equal downstream scores preserve retrieval input order."}</p>
    ${native ? `<p class="method-note">Native structures: ${esc(native.classes.join(", ") || "none indexed")}. Index ${esc(query.index_sha256?.slice(0, 16))} · model ${esc(query.model_sha256?.slice(0, 16) || "not used")}.</p>` : ""}
    </details><div class="premise-controls"><label>Candidate family <select class="premise-family"><option value="all">All families</option>${[
      ...new Set(rows.map((r) => r.family)),
    ]
      .filter(Boolean)
      .map((f) => `<option value="${esc(f)}">${esc(f)}</option>`)
      .join(
        "",
      )}</select></label><label><input type="checkbox" class="premise-selected" /> Selected only</label><label><input type="checkbox" class="premise-all" /> Show complete index results</label></div>
    <details class="premise-changes"><summary>${query.entered?.length || 0} entered · ${query.displaced?.length || 0} displaced actions</summary><p class="method-note">Entered: ${esc(query.entered?.join("; ") || "none")}. Displaced: ${esc(query.displaced?.join("; ") || "none")}.</p></details>
    <p class="premise-count method-note"></p><div class="premise-table table-scroll"></div>`;
  const paint = () => {
    const family = container.querySelector(".premise-family").value;
    const selectedOnly = container.querySelector(".premise-selected").checked;
    const complete = container.querySelector(".premise-all").checked;
    const filtered = rows
      .filter(
        (r) =>
          (family === "all" || r.family === family) &&
          (!selectedOnly || r.selected),
      )
      .sort(
        (a, b) =>
          b.selected - a.selected ||
          (a.actual_rank ?? 999) - (b.actual_rank ?? 999),
      );
    const shown = complete ? filtered : filtered.slice(0, 24);
    container.querySelector(".premise-count").textContent =
      `Showing ${shown.length} of ${filtered.length} recorded proposals. Remaining rows stay in the exported genuine trace; unselected actions were not executed.`;
    container.querySelector(".premise-table").innerHTML =
      `<table><thead><tr><th>Pool / rank</th><th>Candidate and native type</th><th>Compatibility / premises</th><th>Deterministic / learned retrieval</th><th>Action scores</th><th>Actual evidence</th></tr></thead><tbody>${shown.map((r) => `<tr class="${r.selected ? "premise-picked" : ""}"><td data-label="Pool / actual rank">${r.selected ? "Selected" : "Outside cap"}${r.protected ? " · protected" : ""}<br/>${r.actual_rank ?? "—"}</td><td data-label="Candidate and native type"><code>${esc(r.tactic)}</code><details><summary>${esc(r.declaration || r.family || "structural proposal")}</summary><pre class="continuation-code">${esc(r.type || "Structural/local action; exact context type is shown in the native state")}</pre><p class="method-note">${sourceUrl(r.source_module) ? `<a href="${esc(sourceUrl(r.source_module))}" target="_blank" rel="noreferrer">${esc(r.source_module)} ↗</a>` : esc(r.source_module || r.candidate?.provenance || "native local context")}${r.implicit_parameters !== undefined ? ` · ${r.implicit_parameters} implicit / ${r.instance_parameters} instance parameters` : ""}</p>${r.term ? `<p>Witness <code>${esc(r.term)}</code> : <code>${esc(r.type)}</code><br/>Expected <code>${esc(r.expected_type)}</code><br/>${esc(r.construction)} · depth ${r.construction_depth}</p>` : ""}</details></td><td data-label="Compatibility / premises">${r.compatible == null ? "No native probe" : r.compatible ? "Potentially compatible" : "Incompatible probe"}<br/>${esc(r.compatibility_kind || "")}<pre class="continuation-code">${esc((r.premises || []).join("\n"))}</pre>${r.unresolved_explicit_data !== undefined ? `${r.unresolved_explicit_data} unresolved data parameters` : ""}${r.rewritten_target ? `<pre class="continuation-code">↦ ${esc(r.rewritten_target)}</pre>` : ""}</td><td data-label="Retrieval scores / ranks">${number(r.deterministic_score)} / ${number(r.learned_score)}<br/>Score ranks ${r.deterministic_rank ?? "—"} / ${r.learned_rank ?? "—"}<details><summary>Top eight model components</summary><pre class="continuation-code">${esc((r.learned_contributions || []).map(([n, v]) => `${n}: ${number(v)}`).join("\n") || "No fitted score computed for this proposal")}</pre></details></td><td data-label="Action scores">Hand ${number(r.heuristic_score, 1)}<br/>P3 ${number(r.p3_score)}</td><td data-label="Actual evidence">${esc(r.evidence)}</td></tr>`).join("")}</tbody></table>`;
  };
  container
    .querySelectorAll("select,input")
    .forEach((el) => (el.onchange = paint));
  paint();
}
