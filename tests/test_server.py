from __future__ import annotations

from fastapi.testclient import TestClient

from prooflab.server import app

client = TestClient(app)


def test_health_and_task_dataset() -> None:
    assert client.get("/api/health").json()["tasks"] >= 60
    assert len(client.get("/api/tasks").json()) >= 60


def test_no_arbitrary_lean_or_tactic_input_endpoint() -> None:
    response = client.post(
        "/api/search",
        json={
            "task_id": "imp_chain",
            "source": "run_tac ...",
            "tactic": "sorry",
        },
    )
    assert response.status_code == 422
    assert client.post("/api/search", json={"task_id": "../../etc/passwd"}).status_code == 404


def test_cross_origin_computation_and_dns_rebinding_are_rejected() -> None:
    assert (
        client.post(
            "/api/search",
            json={"task_id": "imp_chain"},
            headers={"Origin": "https://attacker.example"},
        ).status_code
        == 403
    )
    assert client.get("/api/health", headers={"Host": "attacker.example"}).status_code == 400
    assert (
        client.post(
            "/api/search", json={"task_id": "imp_chain"}, headers={"Sec-Fetch-Site": "cross-site"}
        ).status_code
        == 403
    )


def test_large_budget_and_unknown_job_are_rejected() -> None:
    assert (
        client.post(
            "/api/search", json={"task_id": "imp_chain", "budget": {"max_depth": 999}}
        ).status_code
        == 422
    )
    assert client.get("/api/jobs/unknown").status_code == 404
    assert client.delete("/api/jobs/unknown").status_code == 404


def test_phase2_dataset_and_real_model_metadata() -> None:
    rows = client.get("/api/tasks?dataset=phase2").json()
    assert len(rows) == 24 and all(t["id"].startswith("p2_") for t in rows)
    model = client.get("/api/model").json()
    assert model["weights"] and len(model["sha256"]) == 64
    assert not model["provenance"]["evaluation_accessed_during_selection"]
    assert client.get("/api/tasks?dataset=unknown").status_code == 422


def test_phase3_model_and_finite_continuation_records() -> None:
    assert len(client.get("/api/tasks?dataset=phase3").json()) == 32
    model = client.get("/api/model?variant=outcome").json()
    assert model["variant"] == "outcome" and model["weights"]
    index = client.get("/api/continuations").json()
    assert any(e["role"] == "development" for e in index)
    bundle = client.get("/api/continuations/development/and_swap").json()
    assert bundle["record"]["source_verification"]["verified"]
    assert bundle["annotations"]["0"]
    assert client.get("/api/continuations/development/unknown").status_code == 404


def test_phase4_finite_dataset_and_frontier_model():
    tasks = client.get("/api/tasks?dataset=phase4")
    assert tasks.status_code == 200 and len(tasks.json()) == 32
    model = client.get("/api/state-model").json()
    assert model["mode"] == "linear" and len(model["sha256"]) == 64
    assert not model["provenance"]["evaluation_accessed"]
