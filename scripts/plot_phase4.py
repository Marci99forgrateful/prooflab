"""Publication-style plots from actual Phase 4 measurement records."""

import os

os.environ.setdefault("MPLCONFIGDIR", "/workspace/.cache/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from prooflab.lean import ROOT
from prooflab.research_io import read_json


def main():
    s = read_json(ROOT / "experiments/phase4/evaluation-v1/summary.json")
    analysis = read_json(ROOT / "experiments/phase4/evaluation-v1/analysis.json")
    names = [
        "bfs",
        "best_first",
        "learned",
        "outcome",
        "frontier",
        "joint",
        "beam",
        "automation",
        "grind",
    ]
    labels = [
        "BFS",
        "Handcrafted",
        "Phase 2",
        "Phase 3",
        "Frontier + hand",
        "Frontier + P3",
        "Beam",
        "Aesop*",
        "grind*",
    ]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), layout="constrained")
    colors = ["#9baea0"] * len(names)
    colors[5] = "#34704a"
    axes[0].barh(labels, [s["results"][n]["verified"] / 2 for n in names], color=colors)
    axes[0].set(
        xlim=(0, 32), xlabel="Verified theorems / 32", title="No frontier success advantage"
    )
    axes[0].invert_yaxis()
    for i, n in enumerate(names):
        axes[0].text(
            s["results"][n]["verified"] / 2 + 0.3,
            i,
            str(s["results"][n]["verified"] // 2),
            va="center",
            fontsize=9,
        )
    bases = ["best_first", "outcome", "frontier"]
    for j, level in enumerate(["theorem", "family"]):
        ds = [
            analysis["comparisons"][a]["common_verified"]["attempted_candidates"][level]
            for a in bases
        ]
        axes[1].errorbar(
            [d["estimate"] for d in ds],
            [i + (j - 0.5) * 0.16 for i in range(len(ds))],
            xerr=[
                [d["estimate"] - d["lower"] for d in ds],
                [d["upper"] - d["estimate"] for d in ds],
            ],
            fmt="o",
            capsize=4,
            label=level + " clusters",
            color=["#34704a", "#ba8036"][j],
        )
    axes[1].axvline(0, color="#999", linewidth=1)
    axes[1].set(
        yticks=range(3),
        yticklabels=["vs handcrafted", "vs Phase 3", "vs frontier + hand"],
        xlabel="Joint − comparator attempts, 95% CI",
        title="Common-verified subset only",
    )
    axes[1].invert_yaxis()
    axes[1].legend(fontsize=8)
    cases = ["p4_contra_disj", "p4_cubic_pair", "p4_partition_nested", "p4_witness_exists"]
    for j, a in enumerate(["best_first", "joint"]):
        axes[2].barh(
            [i + (j - 0.5) * 0.35 for i in range(4)],
            [s["per_theorem"][i]["algorithms"][a]["attempted_candidates"] for i in cases],
            height=0.35,
            label=["handcrafted", "joint"][j],
            color=["#9baea0", "#34704a"][j],
        )
    axes[2].set(
        yticks=range(4),
        yticklabels=["Contraposition†", "Cubic pair", "Set partition", "Witness"],
        xlabel="Actual candidate attempts",
        title="Measured gains and regressions",
    )
    axes[2].invert_yaxis()
    axes[2].legend(fontsize=8)
    fig.suptitle(
        "ProofLab Phase 4 · 640 genuine executions · two deterministic repetitions", fontsize=14
    )
    fig.supxlabel(
        (
            "* Native references have incomparable internal work. "
            "† Joint fails; failed-run attempt counts are not efficiency gains."
        ),
        fontsize=9,
    )
    out = ROOT / "docs/assets"
    for ext in ["svg", "png", "pdf"]:
        fig.savefig(out / f"phase4-results.{ext}", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
