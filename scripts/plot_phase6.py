"""Export scientific plots exclusively from the complete recorded Phase 6 summary."""

from __future__ import annotations

import os

from prooflab.lean import ROOT

os.environ.setdefault("MPLCONFIGDIR", str(ROOT.parent / ".cache/matplotlib"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from prooflab.phase6_evaluation import EXPERIMENT
from prooflab.research_io import read_json


def main() -> None:
    matplotlib.rcParams["svg.hashsalt"] = "prooflab-phase6"
    summary = read_json(EXPERIMENT / "summary.json")
    arms = [
        "phase4",
        "typed5",
        "learned5",
        "deterministic",
        "learned",
        "linear",
        "staged",
        "automation",
        "grind",
    ]
    names = [
        "Expanded P4 / P3",
        "Typed P5",
        "Learned P5",
        "Context hybrid",
        "Learned hybrid",
        "Fully linear hybrid",
        "Staged hybrid",
        "Aesop reference*",
        "grind reference*",
    ]
    rows = [summary["results"][a] for a in arms]
    values = np.array([r["success_rate"] * 100 for r in rows])
    intervals = np.array([r["success_ci95"] for r in rows]) * 100
    fig, (left, right) = plt.subplots(
        1, 2, figsize=(13.6, 6.8), gridspec_kw={"width_ratios": [1.15, 1]}
    )
    colors = ["#738178"] * len(arms)
    colors[4] = "#34704a"
    colors[3] = "#659278"
    y = np.arange(len(arms))
    left.barh(y, values, color=colors, height=0.67)
    left.errorbar(
        values,
        y,
        xerr=np.array(
            [np.maximum(0, values - intervals[:, 0]), np.maximum(0, intervals[:, 1] - values)]
        ),
        fmt="none",
        ecolor="#26392f",
        capsize=3,
        linewidth=1,
    )
    left.set(
        yticks=y,
        yticklabels=names,
        xlim=(0, 100),
        xlabel="Independently verified theorem success (%)",
        title="New frozen benchmark · 48 statements",
    )
    left.invert_yaxis()
    left.grid(axis="x", alpha=0.2)
    left.set_axisbelow(True)
    for i, r in enumerate(rows):
        left.text(
            min(98, values[i] + 1.2), i, f"{r['verified']}/{r['runs']}", va="center", fontsize=8
        )
    comparisons = [
        "learned minus phase4",
        "deterministic minus phase4",
        "learned minus deterministic",
    ]
    labels = ["Learned − strongest P4", "Context hybrid − strongest P4", "Learned − context hybrid"]
    for i, name in enumerate(comparisons):
        r = summary["comparisons"][name]["success"]
        point = r["mean_difference"] * 100
        lo, hi = [x * 100 for x in r["ci95_theorem"]]
        right.errorbar(
            point,
            i,
            xerr=[[max(0, point - lo)], [max(0, hi - point)]],
            fmt="o",
            color="#34704a",
            capsize=4,
        )
    right.axvline(0, color="#8b948e", linewidth=1)
    right.set(
        yticks=np.arange(3),
        yticklabels=labels,
        xlabel="Paired verified-success difference (percentage points)",
        title="Predeclared primary contrasts",
    )
    right.invert_yaxis()
    right.grid(axis="x", alpha=0.2)
    right.set_axisbelow(True)
    for ax in (left, right):
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=9)
    fig.suptitle(
        "ProofLab Phase 6 · measured hybrid search",
        fontsize=17,
        fontweight="bold",
        x=0.07,
        ha="left",
    )
    fig.text(
        0.07,
        0.045,
        "Bars: theorem-bootstrap 95% intervals. Paired contrasts use theorem repeat averages, "
        "10,000 draws, seed 2718.\n*External engines: one two-second call; internal work differs. "
        "ProofLab: cap 24, 600 attempts, 80 expansions, 18s engine budget.\nCurated related "
        "mathematical families; success, symbolic expressiveness and learning effects "
        "must be interpreted separately.",
        fontsize=8,
        color="#536158",
    )
    fig.tight_layout(rect=(0, 0.13, 1, 0.93), w_pad=3)
    for suffix in ("png", "svg", "pdf"):
        target = ROOT / f"docs/assets/phase6-results.{suffix}"
        metadata = (
            {"Date": None}
            if suffix == "svg"
            else {"CreationDate": None, "ModDate": None}
            if suffix == "pdf"
            else {}
        )
        fig.savefig(target, dpi=180, facecolor="white", metadata=metadata)
        if suffix == "svg":
            target.write_text(
                "\n".join(line.rstrip() for line in target.read_text().splitlines()) + "\n"
            )
    print("Exported actual Phase 6 results as PNG/SVG/PDF")


if __name__ == "__main__":
    main()
