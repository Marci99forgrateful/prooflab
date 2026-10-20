"""Standalone figures from actual Phase 3 observations and cluster intervals."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
report = json.loads((ROOT / "experiments/phase3/evaluation-v1/summary.json").read_text())
sensitivity = json.loads(
    (ROOT / "experiments/phase3/evaluation-v1/family-sensitivity.json").read_text()
)
algorithms = [
    "bfs",
    "best_first",
    "learned",
    "outcome",
    "automation",
    "applicability_only",
    "old_features_outcome",
]
labels = ["BFS", "Handcrafted", "Phase 2", "Phase 3", "Native Aesop", "No outcome", "Old + outcome"]
colors = ["#c3cec6", "#7b9d84", "#4f7e65", "#203f2b", "#b9b1a1", "#93b3a9", "#d1c391"]
fig, axes = plt.subplots(1, 3, figsize=(14, 4.2), layout="constrained")
for i, a in enumerate(algorithms):
    g = report["results"][a]
    ci = g["success_interval"]
    axes[0].bar(i, 100 * ci["estimate"], color=colors[i])
    axes[0].errorbar(
        i,
        100 * ci["estimate"],
        yerr=[[100 * (ci["estimate"] - ci["lower"])], [100 * (ci["upper"] - ci["estimate"])]],
        color="#111",
        capsize=3,
    )
    axes[1].bar(i, g["mean_candidates"], color=colors[i])
axes[0].set(
    ylabel="Verified runs (%)", ylim=(0, 105), title="32 frozen theorems; repeats clustered"
)
axes[1].set(
    ylabel="Mean external candidate attempts", title="All tasks, including bounded failures"
)
for ax in axes[:2]:
    ax.set_xticks(range(len(algorithms)), labels, rotation=45, ha="right")
    ax.spines[["top", "right"]].set_visible(False)
base = ["best_first", "learned", "applicability_only", "old_features_outcome"]
for i, a in enumerate(base):
    ci = sensitivity["comparisons"][a]
    axes[2].errorbar(
        ci["estimate"],
        i,
        xerr=[[ci["estimate"] - ci["lower"]], [ci["upper"] - ci["estimate"]]],
        fmt="o",
        color="#325c3d",
        capsize=4,
    )
axes[2].axvline(0, color="#999", lw=1)
axes[2].set(
    yticks=range(4),
    yticklabels=["Handcrafted", "Phase 2", "No outcome", "Old + outcome"],
    xlabel="Phase 3 − baseline attempts",
    title="Supplementary family-cluster 95% CI",
)
axes[2].spines[["top", "right"]].set_visible(False)
fig.supxlabel(
    "Aesop internal work differs from external attempt counts. "
    "Eight-family sensitivity is exploratory; intervals include no gain.",
    fontsize=9,
)
for suffix in ("svg", "png", "pdf"):
    fig.savefig(ROOT / f"docs/assets/phase3-results.{suffix}", dpi=180)
