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
