# ruff: noqa: E501
"""Generate faithful static replay assets from canonical Phase 4 research files."""

import json

from prooflab.lean import ROOT
from prooflab.research_io import read_json, trace_paths

RESEARCH = [
    (
        "Aesop",
        "Safe/unsafe AND/OR rule applications, priority queues and native reconstruction.",
        "https://github.com/leanprover-community/aesop",
        "Installed separate native reference; scheduling implementation independently written.",
    ),
    (
        "TacticToe",
        "Learned tactics and state values from real proof trajectories in HOL4.",
        "https://arxiv.org/abs/1804.00596",
        "Motivates CPU trajectory learning; different logic and library, no numerical reproduction.",
    ),
    (
        "ReProver / LeanDojo",
        "Retrieval-augmented tactic generation, best-first states and premise accessibility.",
        "https://github.com/lean-dojo/ReProver",
        "Separate actor and state scheduling; our scalar model uses no large pretrained model.",
    ),
    (
        "HyperTree Proof Search",
        "Hyperedges jointly require all subgoals; online policy/critic backups and cycle handling.",
        "https://arxiv.org/abs/2205.11491",
        "Conceptual comparison. Shared Lean constraints preclude casual state merging; CC-BY-NC code not copied.",
    ),
    (
        "grind / Duper",
        "Congruence reasoning and E-matching versus given-clause higher-order superposition.",
        "https://github.com/leanprover-community/duper",
        "Installed grind is a separate local reference; Duper is studied in pinned source, not reproduced.",
    ),
    (
        "Sledgehammer / LeanHammer",
        "Premise relevance, ATP portfolios and certified proof reconstruction.",
        "https://github.com/JOSHCLUNE/LeanHammer",
        "Informs isolated local generator study; no cloud premise selection or external inference.",
    ),
    (
        "DeepSeek V1.5 / V2",
        "Exploratory RMaxTS versus recursive subgoal synthesis and verifier-based RL.",
        "https://arxiv.org/abs/2504.21801",
        "Large-model systems studied architecturally, not installed on this CPU host.",
    ),
    (
        "Beam / learned best-first",
        "Bounded priority queue retains promising states, but can evict the only proof.",
        "https://github.com/Marci99forgrateful/prooflab",
        "Established search ideas, original deterministic ProofLab engineering. Not MCTS or admissible A*.",
    ),
    (
        "LeanExplore / Pantograph",
        "Declaration indexes and full native saved elaboration states.",
        "https://github.com/leanprover/Pantograph",
        "No hosted retrieval dependency. Offline native repeated-shape grouping never prunes.",
    ),
]


def main():
    experiment = ROOT / "experiments/phase4/evaluation-v1"
    destination = ROOT / "web/public/phase4"
    (destination / "data/traces").mkdir(parents=True, exist_ok=True)
    manifest = []
    for path in trace_paths(experiment / "traces"):
        data = read_json(path)
        filename = path.name.removesuffix(".gz")
        (destination / "data/traces" / filename).write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
        manifest.append(
            dict(
                task_id=data["task"]["id"],
                algorithm=data["algorithm"],
                repeat=int(data["metadata"]["repeat"]),
                url=f"phase4/data/traces/{filename}",
                status=data["status"],
            )
        )
    native = {}
    native_index = ROOT / "experiments/phase4/native-states-v1/index.json"
    if native_index.exists():
        for task in read_json(native_index)["tasks"]:
            native.update(task["statistics"])
    failures = read_json(ROOT / "experiments/phase4/failures-v1/index.json")
    study_path = ROOT / "experiments/phase4/generator-v1/summary.json"
    study = read_json(study_path) if study_path.exists() else {}
    payload = dict(
        manifest=manifest,
        tasks=json.loads((ROOT / "benchmarks/phase4/evaluation.json").read_text()),
        native=native,
        summary=read_json(experiment / "summary.json"),
        research=[dict(title=t, idea=i, url=u, relation=r) for t, i, u, r in RESEARCH],
        limitations={
            ident: (
                f"Separate generator arm: original {value['original']['status']}; "
                f"extended {value['extended']['status']} with "
                f"{value['extended']['metrics']['attempted_candidates']} tactic calls. "
                "This arm adds general local simplification, lattice premise proposals "
                "and rewriting normalization; its different candidate set is excluded "
                "from primary scheduling comparisons. A simplifier call can perform "
                "many internal inferences. These outcomes never trained or selected models."
            )
            for ident, value in study.get("per_theorem", {}).items()
        },
        phase3_failure_taxonomy=failures,
    )
    (destination / "explorer.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    )
    print(
        "Exported", len(manifest), "genuine runs with", len(native), "native diagnostic summaries"
    )


if __name__ == "__main__":
    main()
