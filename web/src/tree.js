export const escapeHtml = (text) => String(text ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));

// A deterministic tidy tree. Every rendered item corresponds to a recorded attempt.
export function layoutTree(nodes) {
  const children = new Map(nodes.map(n => [n.id, []]));
  for (const n of nodes) if (n.parent !== null && children.has(n.parent)) children.get(n.parent).push(n.id);
  const positions = new Map();
  let leaf = 0;
  function visit(id) {
    const descendants = children.get(id) || [];
    const xs = descendants.map(visit);
    const x = xs.length ? (xs[0] + xs.at(-1)) / 2 : leaf++ * 125;
    const n = nodes.find(n => n.id === id);
    positions.set(id, {x, y: n.depth * 112});
    return x;
  }
  if (nodes.length) visit(nodes[0].id);
  return positions;
}

export function treeMarkup(nodes, selected = 0) {
  const positions = layoutTree(nodes);
  let result = '';
  for (const node of nodes) {
    if (node.parent === null || !positions.has(node.parent)) continue;
    const p = positions.get(node.parent), q = positions.get(node.id);
    const proof = node.on_proof_path;
    result += `<path class="tree-edge ${proof ? 'proof-edge' : ''} ${['rejected','error'].includes(node.status) ? 'rejected-edge' : ''}" d="M${p.x},${p.y} C${p.x},${p.y + 56} ${q.x},${q.y - 56} ${q.x},${q.y}"/>`;
  }
  for (const node of nodes) {
    const p = positions.get(node.id), failed = ['rejected','error'].includes(node.status);
    const label = node.status === 'solved' ? '✓' : failed ? '×' : node.parent === null ? '⊢' : node.state?.goals.length;
    result += `<g class="tree-node ${node.status} ${node.on_proof_path ? 'on-path' : ''} ${node.id === selected ? 'selected-node' : ''}" transform="translate(${p.x},${p.y})" data-node="${node.id}" tabindex="0" role="button" aria-label="State ${node.id}, ${escapeHtml(node.tactic || 'initial goal')}, ${node.status}"><title>${escapeHtml(node.tactic || 'Initial goal')} · ${node.status}</title><circle r="${failed ? 13 : 21}"/><text class="node-symbol" text-anchor="middle" dominant-baseline="central">${escapeHtml(label)}</text><text class="node-tactic" text-anchor="middle" y="40">${escapeHtml((node.tactic || 'initial goal').slice(0, 23))}</text></g>`;
  }
  return {markup: result, positions};
}
