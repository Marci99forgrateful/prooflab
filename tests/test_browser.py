from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, expect, sync_playwright

from prooflab.lean import ROOT, stop_process

pytestmark = pytest.mark.browser


@pytest.fixture(scope="module")
def app_url() -> Iterator[str]:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        [str(ROOT / ".venv/bin/prooflab"), "serve", "--port", str(port)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        start_new_session=True,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen(url + "/api/health", timeout=1) as response:
                    if response.status == 200:
                        break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.05)
        else:
            raise RuntimeError("Local application failed to start")
        yield url
    finally:
        stop_process(process)


@pytest.fixture(scope="module")
def browser() -> Iterator[Browser]:
    with sync_playwright() as p:
        executable = os.environ.get("PROOFLAB_CHROMIUM") or shutil.which("chromium")
        browser = p.chromium.launch(
            executable_path=executable, headless=True, args=["--no-sandbox"]
        )
        yield browser
        browser.close()


@pytest.fixture
def page(browser: Browser, app_url: str) -> Iterator[Page]:
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(app_url, wait_until="networkidle")
    expect(page.locator("#metric-status")).to_have_text("✓ Verified")
    yield page
    assert not errors
    page.close()


def test_authentic_tree_goal_inspection_and_download(page: Page) -> None:
    expect(page.locator("#mode-badge")).to_have_text("Recorded replay")
    page.locator('.tree-node[data-node="3"]').click()
    expect(page.locator("#selected-tactic")).not_to_have_text("Initial goal")
    expect(page.locator("#hypotheses")).to_contain_text("hp")
    with page.expect_download() as download:
        page.locator("#download-proof").click()
    source = download.value.path().read_text()
    assert "apply hqr" in source and "#prooflab_audit prooflab_result" in source
    assert "sorry" not in source


def test_replay_pause_step_speed_zoom_and_theme(page: Page) -> None:
    page.locator("#timeline").fill("1")
    expect(page.locator(".tree-node")).to_have_count(1)
    page.locator("#step-button").click()
    expect(page.locator(".tree-node")).to_have_count(2)
    page.locator("#speed").select_option("25")
    page.locator("#play-toggle").click()
    expected = page.locator("#timeline").get_attribute("max")
    assert expected is not None
    expect(page.locator("#timeline")).to_have_value(expected)
    assert page.evaluate("""() => {
        const area = document.querySelector('#tree-svg').getBoundingClientRect();
        return [...document.querySelectorAll('#tree-svg .tree-node circle')].every(circle => {
            const box = circle.getBoundingClientRect();
            return box.left >= area.left && box.right <= area.right;
        });
    }""")
    before = page.locator("#tree-transform").get_attribute("transform")
    page.locator("#zoom-in").click()
    assert before != page.locator("#tree-transform").get_attribute("transform")
    page.locator("#theme-toggle").click()
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")


def test_compare_and_actual_benchmark_views(page: Page) -> None:
    page.locator('[data-view="compare"]').click()
    expect(page.locator("#comparison-grid .card")).to_have_count(2)
    expect(page.locator("#comparison-grid")).to_contain_text("Systematic breadth-first")
    expect(page.locator("#comparison-grid")).to_contain_text("Heuristic best-first")
    page.locator('[data-view="benchmarks"]').click()
    expect(page.locator("#benchmark-content")).to_contain_text("Native Aesop")
    expect(page.locator("#benchmark-content")).to_contain_text("EXPERIMENT PROVENANCE")


@pytest.mark.parametrize("width,height", [(390, 844), (768, 1024), (1440, 1000)])
def test_responsive_layout_has_no_horizontal_overflow(page: Page, width: int, height: int) -> None:
    page.set_viewport_size({"width": width, "height": height})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    expect(page.locator("#run-button")).to_be_visible()


def test_local_new_computation_is_verified_in_real_lean(page: Page) -> None:
    page.locator("#mode-toggle").click()
    expect(page.locator("#mode-badge")).to_have_text("Live local search")
    page.locator("#run-button").click()
    expect(page.locator("#notice")).to_contain_text(
        "New computation completed: verified", timeout=45000
    )
    expect(page.locator("#proof-code")).to_contain_text("apply hqr")


def test_keyboard_node_inspection_and_svg_export(page: Page) -> None:
    node = page.locator('.tree-node[data-node="1"]')
    node.focus()
    page.keyboard.press("Enter")
    expect(page.locator("#node-label")).to_have_text("STATE 01")
    with page.expect_download() as download:
        page.locator("#export-svg").click()
    svg = download.value.path().read_text()
    assert "<svg" in svg and "data-node" in svg


def test_full_trace_export_preserves_recorded_nodes(page: Page) -> None:
    with page.expect_download() as download:
        page.locator("#export-trace").click()
    trace = json.loads(download.value.path().read_text())
    assert trace["task"]["id"] == "imp_chain"
    assert trace["verification"]["verified"] is True
    assert trace["metrics"]["attempted_candidates"] == len(trace["nodes"]) - 1


def test_static_subdirectory_demo_requires_no_backend_or_cdn(
    browser: Browser, tmp_path: Path
) -> None:
    (tmp_path / "prooflab").symlink_to(ROOT / "web/dist", target_is_directory=True)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        [
            str(ROOT / ".venv/bin/python"),
            "-m",
            "http.server",
            str(port),
            "--bind",
            "127.0.0.1",
            "--directory",
            str(tmp_path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        start_new_session=True,
    )
    page = browser.new_page(viewport={"width": 1200, "height": 900})
    url = f"http://127.0.0.1:{port}"
    external = []
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(url, timeout=1).close()
                break
            except urllib.error.URLError:
                time.sleep(0.05)
        page.on(
            "request", lambda req: external.append(req.url) if not req.url.startswith(url) else None
        )
        page.goto(url + "/prooflab/", wait_until="networkidle")
        expect(page.locator("#metric-status")).to_have_text("✓ Verified")
        expect(page.locator("#mode-badge")).to_have_text("Recorded replay")
        expect(page.locator("#mode-toggle")).to_be_hidden()
        assert not external
    finally:
        page.close()
        stop_process(process)


def test_local_api_cancellation_ends_without_certifying_a_proof(page: Page, app_url: str) -> None:
    response = page.request.post(app_url + "/api/search", data={"task_id": "imp_chain"})
    assert response.status == 202
    ident = response.json()["job_id"]
    assert page.request.delete(app_url + f"/api/jobs/{ident}").status == 200
    for _ in range(100):
        job = page.request.get(app_url + f"/api/jobs/{ident}").json()
        if job["state"] != "running":
            break
        time.sleep(0.05)
    assert job["trace"]["status"] == "cancelled"
    assert not job["trace"]["verification"]["verified"]


def test_learned_rankings_explain_real_execution_and_three_trees(page: Page) -> None:
    page.locator("#dataset-select").select_option("phase2")
    page.locator("#task-select").select_option("p2_congr_nested")
    page.locator('[data-algorithm="learned"]').click()
    expect(page.locator("#metric-status")).to_have_text("✓ Verified")
    expect(page.locator("#rankings-panel")).to_be_visible()
    expect(page.locator("#ranking-note")).to_contain_text(
        "Learned scores determine candidate order"
    )
    expect(page.locator("#ranking-rows tr").first).to_contain_text("rw [h]")
    expect(page.locator("#ranking-rows")).to_contain_text("Not executed")
    page.locator("#ranking-rows details summary").first.click()
    expect(page.locator("#ranking-rows details pre").first).to_contain_text("cross:Eq|rewrite")
    with page.expect_download() as download:
        page.locator("#export-trace").click()
    trace = json.loads(download.value.path().read_text())
    assert trace["algorithm"] == "learned" and trace["verification"]["verified"]
    assert trace["rankings"][0]["candidates"][0]["tactic"] == "rw [h]"
    page.locator("#repeat-select").select_option("2")
    expect(page.locator("#proof-method")).to_contain_text("repeat 3 of 3")
    with page.expect_download() as download:
        page.locator("#export-trace").click()
    trace = json.loads(download.value.path().read_text())
    assert trace["metadata"]["repeat"] == "2"
    page.locator('[data-view="compare"]').click()
    page.locator("#compare-task").select_option("p2_congr_nested")
    expect(page.locator("#comparison-grid .card")).to_have_count(3)
    expect(page.locator("#comparison-grid")).to_contain_text("Learned candidate ranking")
    page.locator('[data-view="benchmarks"]').click()
    expect(page.locator("#benchmark-content")).to_contain_text("Learned ranker")
    expect(page.locator("#benchmark-content")).to_contain_text("95% CI")
    expect(page.locator("#benchmark-content")).to_contain_text("288")
    page.locator("#dataset-select").select_option("phase1")
    page.locator('[data-view="lab"]').click()
    page.locator('[data-algorithm="best_first"]').click()
    expect(page.locator("#metric-status")).to_have_text("✓ Verified")


def test_live_learned_search_is_a_new_verified_computation(page: Page) -> None:
    # Development task regression; not a new model-selection experiment.
    page.locator('[data-algorithm="learned"]').click()
    page.locator("#mode-toggle").click()
    page.locator("#run-button").click()
    expect(page.locator("#notice")).to_contain_text(
        "New computation completed: verified", timeout=45000
    )
    expect(page.locator("#rankings-panel")).to_be_visible()
    expect(page.locator("#proof-method")).to_contain_text("Learned")


def test_phase3_actual_rankings_and_five_policy_comparison(page: Page) -> None:
    page.locator("#dataset-select").select_option("phase3")
    page.locator("#task-select").select_option("p3_order_guard")
    page.locator('[data-algorithm="outcome"]').click()
    expect(page.locator("#metric-status")).to_have_text("✓ Verified")
    expect(page.locator("#ranking-note")).to_contain_text(
        "Outcome scores determine candidate order"
    )
    expect(page.locator("#outcome-ranking-header")).to_be_visible()
    expect(page.locator("#proof-method")).to_contain_text("Outcome-aware")
    with page.expect_download() as download:
        page.locator("#export-trace").click()
    trace = json.loads(download.value.path().read_text())
    assert trace["algorithm"] == "outcome" and trace["verification"]["verified"]
    assert trace["rankings"][0]["candidates"][0]["outcome_score"] is not None
    page.locator('[data-view="compare"]').click()
    page.locator("#compare-task").select_option("p3_relation_reverse")
    expect(page.locator("#comparison-grid .card")).to_have_count(5)
    expect(page.locator("#comparison-grid")).to_contain_text("Native Aesop reference")
    expect(page.locator("#comparison-grid")).to_contain_text("Outcome-aware ranking")
    page.locator('[data-view="benchmarks"]').click()
    expect(page.locator("#benchmark-content")).to_contain_text("384")
    expect(page.locator("#benchmark-content")).to_contain_text("Ablation: applicability only")


def test_actual_valid_continuations_costs_censoring_and_export(page: Page) -> None:
    from prooflab.research import manifest

    entries = manifest()
    page.locator('[data-view="continuations"]').click()
    page.locator("#continuation-state-select").select_option("development:and_swap:0")
    expect(page.locator("#continuation-role")).to_contain_text(
        "Development evidence used for training"
    )
    expect(page.locator("#continuation-context")).to_contain_text("Q ∧ P")
    expect(page.locator("#continuation-rows")).to_contain_text("verified completion")
    expect(page.locator("#continuation-left")).to_contain_text("fresh audit time")
    expect(page.locator("#continuation-right")).to_contain_text("fresh audit time")
    page.locator('#continuation-left .tree-node[data-node="1"]').click()
    expect(page.locator("#continuation-left .continuation-node-label")).to_contain_text(
        "Actual state 1"
    )
    expect(page.locator("#continuation-left .continuation-node-state")).to_contain_text("⊢")
    before = page.locator("#continuation-left svg").get_attribute("viewBox")
    page.locator('#continuation-left [data-czoom="in"]').click()
    assert before != page.locator("#continuation-left svg").get_attribute("viewBox")
    assert (
        page.locator("#continuation-left .tree-node").count()
        != page.locator("#continuation-right .tree-node").count()
    )
    with page.expect_download() as download:
        page.locator("#export-continuations").click()
    data = json.loads(download.value.path().read_text())
    assert data["record"]["task_id"] == "and_swap" and data["source_sha256"]
    assert data["annotations"]["0"][0]["outcome_score"] is not None
    censored = next(e for e in entries if e["explored"] > e["verified"])
    page.locator("#continuation-state-select").select_option(censored["key"])
    expect(page.locator("#continuation-rows")).to_contain_text("bounded unresolved")
    options = page.locator("#continuation-left-select option").all_text_contents()
    index = next(i for i, text in enumerate(options) if "bounded unresolved" in text)
    page.locator("#continuation-left-select").select_option(str(index))
    expect(page.locator("#continuation-left")).to_contain_text("not evidence of impossibility")
    diagnostic = next(
        e for e in entries if e["role"] == "diagnostic" and e["case"]["kind"] == "higher_cost"
    )
    page.locator("#continuation-state-select").select_option(diagnostic["key"])
    expect(page.locator("#continuation-role")).to_contain_text("never training data")
    expect(page.locator("#continuation-case")).to_contain_text("local regression")
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_live_outcome_search_keeps_independent_verification(page: Page) -> None:
    page.locator('[data-algorithm="outcome"]').click()
    page.locator("#mode-toggle").click()
    page.locator("#run-button").click()
    expect(page.locator("#notice")).to_contain_text(
        "New computation completed: verified", timeout=45000
    )
    expect(page.locator("#proof-method")).to_contain_text("Outcome-aware")
    expect(page.locator("#outcome-ranking-header")).to_be_visible()


def test_architecture_actual_frontier_and_comparison_export(page: Page) -> None:
    page.locator('[data-view="architecture"]').click()
    expect(page.locator("#arch-side-1 .arch-state-title")).to_contain_text("State 0")
    page.locator("#arch-task").select_option("p4_cubic_pair")
    expect(page.locator("#arch-side-1 .arch-metrics span").first).to_contain_text("146")
    page.locator("#arch-step").fill("6")
    expect(page.locator("#arch-divergence")).to_contain_text("Different actual prefixes")
    expect(page.locator("#arch-side-1 .arch-value")).to_contain_text(
        "predicted log continuation cost"
    )
    expect(page.locator("#arch-side-1 .arch-tree-note")).to_contain_text("Actual neighborhood")
    page.locator("#arch-side-1 .arch-whole").click()
    expect(page.locator("#arch-side-1 .arch-node")).to_have_count(147)
    page.locator("#arch-side-1 summary", has_text="Repeated-state relationships").click()
    expect(page.locator("#arch-side-1 .arch-repeats")).to_contain_text("Offline native diagnostics")
    with page.expect_download() as download:
        page.locator("#arch-export").click()
    payload = json.loads(download.value.path().read_text())
    assert len(payload["traces"]) == 2
    assert payload["traces"][1]["verification"]["verified"]
    assert payload["traces"][1]["metrics"]["attempted_candidates"] == 146
    assert payload["traces"][1]["frontier_decisions"]


def test_architecture_negative_result_and_mobile_layout(page: Page) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator('[data-view="architecture"]').click()
    expect(page.locator("#arch-side-1 .arch-state-title")).to_contain_text("State 0")
    page.locator("#arch-task").select_option("p4_contra_disj")
    expect(page.locator("#arch-side-1 .pill")).to_have_text("not_found_within_budget")
    expect(page.locator("#arch-side-0 .pill")).to_have_text("verified")
    expect(page.locator("#arch-side-1")).to_contain_text("resource_limit:expansions")
    expect(page.locator("#arch-research article")).to_have_count(9)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    assert page.locator("#dataset-select").is_hidden()
    page.locator('[data-view="lab"]').click()
    expect(page.locator("#dataset-select")).to_be_visible()


def test_phase5_native_products_real_scores_and_export(page: Page) -> None:
    page.locator('[data-view="architecture"]').click()
    expect(page.locator("#arch-side-1 .arch-state-title")).to_contain_text("State 0")
    page.locator("#arch-dataset").select_option("phase5")
    expect(page.locator('#arch-task option[value="p5_product_graph"]')).to_have_count(1)
    page.locator("#arch-task").select_option("p5_product_graph")
    expect(page.locator("#arch-side-1 .pill")).to_have_text("verified")
    expect(page.locator("#arch-side-0 .pill")).to_have_text("not_found_within_budget")
    expect(page.locator("#arch-side-1 .arch-premises")).to_contain_text("exists ((a, b))")
    expect(page.locator("#arch-side-1 .arch-premises")).to_contain_text("allocation heartbeats")
    expect(page.locator("#arch-side-1 .premise-table")).to_contain_text(
        "verified complete proof path"
    )
    page.locator("#arch-side-1 .premise-family").select_option("witness")
    page.locator("#arch-side-1 .premise-table details summary").first.click()
    expect(page.locator("#arch-side-1 .premise-table")).to_contain_text(
        "typed product construction"
    )
    with page.expect_download() as download:
        page.locator("#arch-export").click()
    payload = json.loads(download.value.path().read_text())
    right = payload["traces"][1]
    assert right["task"]["id"] == "p5_product_graph" and right["verification"]["verified"]
    assert right["metadata"]["arm"] == "learned_p3"
    assert right["retrievals"][0]["native"]["term_constructions"] <= 48
    assert any(r["learned_score"] is not None for r in right["retrievals"][0]["pool"])
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")


def test_phase5_unexplored_candidates_stay_unknown_and_phase4_return(page: Page) -> None:
    page.locator('[data-view="architecture"]').click()
    expect(page.locator("#arch-side-1 .arch-state-title")).to_contain_text("State 0")
    page.locator("#arch-dataset").select_option("phase5")
    expect(page.locator('#arch-task option[value="p5_product_graph"]')).to_have_count(1)
    page.locator("#arch-task").select_option("p5_product_graph")
    expect(page.locator("#arch-side-1 .pill")).to_have_text("verified")
    page.locator("#arch-side-1 .premise-all").check()
    expect(page.locator("#arch-side-1 .premise-table")).to_contain_text(
        "Unexplored in this execution"
    )
    expect(page.locator("#arch-side-1 .premise-table")).to_contain_text("Potentially compatible")
    expect(page.locator("#arch-research article")).to_have_count(5)
    page.locator("#arch-cases summary").click()
    regression = page.locator("#arch-cases article").filter(has_text="Typed generator regression")
    expect(regression).to_have_count(1)
    regression.locator("button").click()
    expect(page.locator("#arch-side-0 .pill")).to_have_text("not_found_within_budget")
    expect(page.locator("#arch-side-1 .pill")).to_have_text("verified")
    page.locator("#arch-dataset").select_option("phase4")
    expect(page.locator('#arch-task option[value="p4_cubic_pair"]')).to_have_count(1)
    expect(page.locator("#arch-research article")).to_have_count(9)
    expect(page.locator("#arch-policy-a")).to_have_value("best_first")


def test_phase5_local_typed_computation_is_a_new_audited_run(page: Page) -> None:
    page.locator('[data-view="architecture"]').click()
    expect(page.locator("#arch-side-1 .arch-state-title")).to_contain_text("State 0")
    page.locator("#arch-dataset").select_option("phase5")
    expect(page.locator('#arch-task option[value="p5_product_graph"]')).to_have_count(1)
    page.locator("#arch-task").select_option("p5_product_graph")
    page.locator("#arch-policy-a").select_option("typed_hand")
    expect(page.locator("#arch-side-0 h2")).to_contain_text("Deterministic typed")
    page.locator("#arch-local").click()
    expect(page.locator("#arch-notice")).to_contain_text(
        "Actual local run: verified", timeout=45000
    )
    with page.expect_download() as download:
        page.locator("#arch-export").click()
    left = json.loads(download.value.path().read_text())["traces"][0]
    assert left["metadata"]["generator_mode"] == "typed"
    assert left["verification"]["verified"] and left["retrievals"]
    assert "repeat" not in left["metadata"]
    expect(page.locator("#arch-dataset")).to_be_enabled()
