# ruff: noqa: E501
"""Publication/export figure from the frozen real Phase 5 experiment."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from prooflab.lean import ROOT
from prooflab.phase5_evaluation import EXPERIMENT
from prooflab.research_io import read_json


def main() -> None:
    summary = read_json(EXPERIMENT / "summary-canonical.json")
    results = summary["results"]
    arms = list(results)
    colors = {
        "original": "#65716a",
        "phase4": "#ac8752",
        "typed": "#458e7f",
        "learned": "#42629a",
        "broad": "#a76b65",
        "type": "#9b8eae",
        "no": "#99927f",
        "automation": "#555d60",
        "grind": "#747c7e",
    }
    fig, axes = plt.subplots(1, 3, figsize=(18, 8), gridspec_kw={"width_ratios": [1.2, 0.85, 1.1]})
    ax = axes[0]
    labels = []
    for i, arm in enumerate(arms):
        row = results[arm]
        point = 100 * row["success_rate"]
        lo, hi = [100 * v for v in row["success_ci95"]]
        ax.barh(i, point, color=colors.get(arm.split("_")[0], "#888888"), height=0.65)
        ax.errorbar(
            point,
            i,
            xerr=[[max(0, point - lo)], [max(0, hi - point)]],
            fmt="none",
            color="#202b27",
            capsize=2,
            lw=1,
        )
        ax.text(point + 1.5, i, f"{row['verified']}/{row['runs']}", va="center", fontsize=8)
        labels.append(arm.replace("_", " ") + (" †" if arm in ("automation", "grind") else ""))
    ax.set(
        yticks=range(len(arms)),
        yticklabels=labels,
        xlim=(0, 118),
        xlabel="Verified runs (%) · theorem bootstrap 95% interval",
        title="Verified success · all frozen arms",
    )
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.18)
    ax.set_axisbelow(True)
    ax = axes[1]
    comparisons = [
        ("typed_p3 minus original_p3", "Typed − original"),
        ("learned_p3 minus typed_p3", "Learned − typed"),
        ("typed_joint minus typed_p3", "Joint − P3 actions"),
    ]
    for i, (key, _label) in enumerate(comparisons):
        row = summary["comparisons"][key]["common_verified"]["attempted_candidates"]
        point = row["mean_difference"]
        if point is None:
            continue
        lo, hi = row["ci95_theorem"]
        ax.errorbar(
            point,
            i,
            xerr=[[max(0, point - lo)], [max(0, hi - point)]],
            fmt="o",
            color="#42629a",
            capsize=4,
        )
        ax.annotate(
            f"n={row['theorems']} common verified",
            (point, i),
            xytext=(0, 13),
            textcoords="offset points",
            ha="center",
            fontsize=8,
        )
    ax.axvline(0, color="#7c827e", lw=1, ls="--")
    ax.set(
        yticks=range(3),
        yticklabels=[label for _, label in comparisons],
        ylim=(-0.6, 2.6),
        xlabel="Mean attempt difference (left − right)\nPaired theorem bootstrap 95% interval",
        title="Effort conditional on common success",
    )
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.18)
    ax = axes[2]
    selected = ["original_p3", "phase4_p3", "typed_p3", "learned_p3", "automation", "grind"]
    components = [
        ("initialization_s", "Initialize", "#bcc4c0"),
        ("verification_s", "Fresh audit", "#8ba99a"),
        ("native_step", "Native step / external engine", "#65716a"),
        ("retrieval_s", "Native retrieval", "#cda267"),
        ("planning_s", "Planning / scoring", "#6597ae"),
    ]
    bottom = [0.0] * len(selected)
    for metric, label, color in components:
        values = []
        for arm in selected:
            m = results[arm]["metrics"]
            value = (
                m["lean_execution_s"]["mean"] - m["retrieval_s"]["mean"]
                if metric == "native_step"
                else m[metric]["mean"]
            )
            values.append(max(0, value))
        ax.bar(range(len(selected)), values, bottom=bottom, label=label, color=color, width=0.65)
        bottom = [a + b for a, b in zip(bottom, values, strict=True)]
    total = [results[a]["metrics"]["elapsed_s"]["mean"] for a in selected]
    ax.scatter(range(len(selected)), total, c="#202b27", marker="_", s=110, label="Total wall")
    ax.set(
        xticks=range(len(selected)),
        xticklabels=[a.replace("_p3", " × P3") for a in selected],
        ylabel="Mean seconds per run",
        title="Shared-host wall-time components",
    )
    ax.tick_params(axis="x", rotation=35)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(axis="y", alpha=0.18)
    ax.set_axisbelow(True)
    fig.suptitle("ProofLab v0.5.0 · type-directed generation and learned retrieval", fontsize=16)
    fig.text(
        0.5,
        0.015,
        "40 original theorems / 10 families · 1120 genuine searches · primary arms twice, ablations once.\n† Native Aesop/grind: one external call with distinct internal work. All-run timing mixes successes and failures; shared host, no hardware-speedup claim.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.08, 1, 0.95), w_pad=3)
    folder = ROOT / "docs/assets"
    folder.mkdir(exist_ok=True)
    for extension in ("png", "svg", "pdf"):
        fig.savefig(folder / f"phase5-results.{extension}", dpi=180, bbox_inches="tight")
    print("Saved genuine Phase 5 PNG/SVG/PDF figures")


if __name__ == "__main__":
    main()
