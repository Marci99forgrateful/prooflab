"""Publication artifacts from measured Phase 2 summary (no synthetic data)."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
report = json.loads((ROOT / "experiments/phase2/evaluation-v1/summary.json").read_text())
algorithms = ["bfs", "best_first", "learned", "automation"]
labels = ["BFS", "Handcrafted", "Learned", "Native Aesop"]
colors = ["#99b8a6", "#56846a", "#233f33", "#b2a895"]
fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.8), layout="constrained")
for i, a in enumerate(algorithms):
    g = report["results"][a]
    ci = g["success_interval"]
    axes[0].bar(i, 100 * ci["estimate"], color=colors[i])
    axes[0].errorbar(
        i,
        100 * ci["estimate"],
        yerr=[[100 * (ci["estimate"] - ci["lower"])], [100 * (ci["upper"] - ci["estimate"])]],
        color="#111111",
        capsize=5,
    )
    axes[1].bar(i, g["mean_candidates"], color=colors[i])
axes[0].set(
    ylabel="Fresh-verified runs (%)",
    ylim=(0, 109),
    title="Frozen evaluation: 24 theorems × 3 repeats",
)
axes[1].set(ylabel="Mean external candidate attempts", title="ProofLab candidate efficiency")
for ax in axes:
    ax.set_xticks(range(4), labels, rotation=15)
    ax.spines[["top", "right"]].set_visible(False)
fig.supxlabel(
    "95% theorem-cluster bootstrap intervals. "
    "Aesop's internal work is not measured as candidate attempts.",
    fontsize=8,
)
for suffix in ("svg", "png", "pdf"):
    fig.savefig(ROOT / f"docs/assets/phase2-results.{suffix}", dpi=180)
