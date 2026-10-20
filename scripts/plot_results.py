"""Create publication-exportable figures from actual trace files, never constants."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from prooflab.models import Trace

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", type=Path)
    args = parser.parse_args()
    report = json.loads((args.experiment / "summary.json").read_text())
    traces = [
        Trace.model_validate_json(p.read_text())
        for p in (args.experiment / "traces").glob("*.json")
    ]
    algorithms = ["bfs", "best_first", "automation"]
    names = ["Breadth-first", "Best-first", "Native Aesop"]
    colors = ["#294c40", "#7eaa6c", "#a7b0a4"]
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
            "axes.titleweight": "medium",
        }
    )
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.9), layout="constrained")
    verified = [report["results"][a]["verified"] for a in algorithms]
    bars = axes[0].bar(names, verified, color=colors, width=0.65)
    for bar, a in zip(bars, algorithms, strict=True):
        n = report["results"][a]["attempted"]
        axes[0].text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"{bar.get_height():.0f}/{n}",
            ha="center",
            fontsize=10,
        )
    axes[0].set(
        ylim=(0, 70), ylabel="Independently verified proofs", title="Success at identical budgets"
    )
    domains = ["logic", "order", "algebra", "sets"]
    xs = np.arange(4)
    for i, a in enumerate(algorithms):
        ys = [report["results"][a]["domains"][d]["verified"] for d in domains]
        axes[1].bar(xs + (i - 1) * 0.25, ys, width=0.23, color=colors[i], label=names[i])
    axes[1].set(
        xticks=xs,
        xticklabels=["Logic", "Orders", "Algebra", "Sets"],
        ylim=(0, 18),
        ylabel="Verified / 16 tasks",
        title="Results by subject",
    )
    axes[1].legend(frameon=False, fontsize=8, loc="upper left")
    indexed = {(t.task.id, t.algorithm): t for t in traces}
    paired = [
        (t, indexed.get((t.task.id, "best_first")))
        for t in traces
        if t.algorithm == "bfs" and t.status == "verified"
    ]
    pairs = [(a, b) for a, b in paired if b is not None and b.status == "verified"]
    x = [a.metrics.expanded_states for a, b in pairs]
    y = [b.metrics.expanded_states for a, b in pairs]
    axes[2].scatter(x, y, color=colors[1], s=28, alpha=0.7, edgecolors=colors[0], linewidths=0.5)
    maximum = max([1, *x, *y]) + 1
    axes[2].plot([1, maximum], [1, maximum], linestyle="--", color="#8e988d", linewidth=0.8)
    axes[2].set(
        xscale="log",
        yscale="log",
        xlabel="Breadth-first expanded states",
        ylabel="Best-first expanded states",
        title=f"Paired verified tasks (n={len(pairs)})",
    )
    fig.suptitle("ProofLab · Phase 1 measured evaluation", fontsize=15, fontweight="medium")
    destination = ROOT / "docs/assets"
    destination.mkdir(exist_ok=True, parents=True)
    for extension in ("svg", "png", "pdf"):
        fig.savefig(
            destination / f"benchmark-results.{extension}",
            dpi=180,
            metadata={"Creator": "ProofLab — actual recorded benchmark results"},
        )
    svg = destination / "benchmark-results.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")
    print(f"Plotted {len(traces)} recorded runs")


if __name__ == "__main__":
    main()
