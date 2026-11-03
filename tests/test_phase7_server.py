from fastapi.testclient import TestClient

from prooflab.server import app

client = TestClient(app)


def test_registered_phase7_tasks_and_model_are_available() -> None:
    response = client.get("/api/tasks?dataset=phase7")
    assert response.status_code == 200 and len(response.json()) == 48
    model = client.get("/api/budget-model")
    assert model.status_code == 200
    assert model.json()["evaluation_accessed"] is False
    assert model.json()["training_ids"]


def test_phase7_search_does_not_accept_source_code_or_unknown_tasks() -> None:
    assert (
        client.post(
            "/api/search", json={"task_id": "imp_chain", "phase7_policy": "joint"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/search", json={"task_id": "p7_test_unknown", "phase7_policy": "joint"}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/search",
            json={"task_id": "p7_test_unknown", "phase7_policy": "joint", "source": "sorry"},
        ).status_code
        == 422
    )
