"""Shareable figures drawn only from the recorded frozen experiment."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from report_phase7 import NAMES

from prooflab.lean import ROOT
from prooflab.phase7_evaluation import EXPERIMENT
from prooflab.research_io import read_json


def main() -> None:
    summary = read_json(EXPERIMENT / "summary.json")
    arms = list(summary["results"])
    values = [summary["results"][a]["verified"] for a in arms]
    colors = [
        "#346b4b"
        if a == "conservative"
        else "#aebdb2"
        if a in ("automation", "grind")
        else "#5d7d8b"
        if a.startswith("phase")
        else "#8fa986"
        for a in arms
    ]
    fig, ax = plt.subplots(figsize=(11, 6.5), layout="constrained")
    bars = ax.barh([NAMES[a] for a in arms], values, color=colors)
    ax.bar_label(bars, labels=[f"{v}/48" for v in values], padding=5, fontsize=10)
    ax.set_xlim(0, 53)
    ax.set_xlabel("Independently Lean-verified statements out of 48")
    ax.set_title("ProofLab v0.7.0 · frozen new-family evaluation", loc="left", fontweight="bold")
    ax.invert_yaxis()
    ax.spines[["top", "right"]].set_visible(False)
    ax.text(
        0,
        -0.14,
        "528 actual runs · same outer 18s / 600 attempts · "
        "native references have opaque internal work",
        transform=ax.transAxes,
        fontsize=9,
        color="#555",
    )
    for extension in ("png", "svg", "pdf"):
        fig.savefig(ROOT / f"docs/assets/phase7-results.{extension}", dpi=170, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
