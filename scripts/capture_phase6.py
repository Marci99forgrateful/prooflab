"""Capture actual integrated Phase 6 replay, with no synthesized proof imagery."""

from __future__ import annotations

import argparse
import os
import shutil

from playwright.sync_api import expect, sync_playwright

from prooflab.lean import ROOT
from prooflab.phase6_evaluation import EXPERIMENT
from prooflab.research_io import read_json


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8006")
    args = p.parse_args()
    index = read_json(ROOT / "web/public/phase6/explorer.json")
    summary = read_json(EXPERIMENT / "summary.json")
    baseline = {r["task_id"]: r["verified"] for r in summary["per_theorem"] if r["arm"] == "phase4"}
    witness = next(
        (
            r
            for r in summary["per_theorem"]
            if r["arm"] == "deterministic"
            and r["verified"]
            and r["verified"] > baseline[r["task_id"]]
            and any(any(t.startswith("exists ") for t in proof) for proof in r["proofs"])
        ),
        None,
    )
    if witness is None:
        raise ValueError("No actual verified witness example available")
    witness_repeat = next(
        e["repeat"]
        for e in index["manifest"]
        if e["task_id"] == witness["task_id"]
        and e["arm"] == "deterministic"
        and e["status"] == "verified"
    )
    with sync_playwright() as play:
        browser = play.chromium.launch(
            executable_path=os.environ.get("PROOFLAB_CHROMIUM") or shutil.which("chromium"),
            headless=True,
            args=["--no-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1600, "height": 1100}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url, wait_until="networkidle")
        page.locator('[data-view="architecture"]').click()
        expect(page.locator("#arch-side-1 .arch-state-title")).to_contain_text("State 0")
        page.locator("#arch-dataset").select_option("phase6")
        expect(page.locator("#arch-task option")).to_have_count(48)
        page.locator("#arch-task").select_option(witness["task_id"])
        page.locator("#arch-policy-a").select_option("phase4")
        page.locator("#arch-policy-b").select_option("deterministic")
        page.locator("#arch-repeat").select_option(str(witness_repeat))
        expect(page.locator("#arch-side-1 h2")).to_have_text(index["policy_names"]["deterministic"])
        expect(page.locator("#arch-side-1 .pill")).to_have_text("verified")
        page.evaluate(
            "window.scrollTo(0,document.querySelector('.arch-comparison').getBoundingClientRect().top+scrollY-12)"
        )
        page.screenshot(path=str(ROOT / "docs/assets/phase6-tree-comparison.png"))
        if page.locator('#arch-side-1 .premise-family option[value="witness"]').count():
            page.locator("#arch-side-1 .premise-family").select_option("witness")
            page.locator("#arch-side-1 .premise-selected").check()
            page.locator("#arch-side-1 .premise-table details summary").first.click()
        page.locator("#arch-side-1 .premise-table tr").last.scroll_into_view_if_needed()
        page.screenshot(path=str(ROOT / "docs/assets/phase6-native-witness.png"))
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#arch-side-1 .adaptive-decision").scroll_into_view_if_needed()
        page.screenshot(path=str(ROOT / "docs/assets/phase6-mobile.png"))
        page.set_viewport_size({"width": 1600, "height": 1100})
        case = next(
            (e for e in index["examples"] if "regression" in e["title"].lower()),
            index["examples"][0] if index["examples"] else None,
        )
        if case:
            page.locator("#arch-task").select_option(case["task_id"])
            page.locator("#arch-policy-a").select_option(case["left"])
            page.locator("#arch-policy-b").select_option(case["right"])
            page.locator("#arch-repeat").select_option(str(case.get("repeat", 0)))
            expect(page.locator("#arch-side-0 h2")).to_have_text(
                index["policy_names"][case["left"]]
            )
            expect(page.locator("#arch-side-1 h2")).to_have_text(
                index["policy_names"][case["right"]]
            )
            page.evaluate(
                "window.scrollTo(0,document.querySelector('.arch-comparison').getBoundingClientRect().top+scrollY-12)"
            )
            page.screenshot(path=str(ROOT / "docs/assets/phase6-regression.png"))
            learned_side = 0 if case["left"] == "learned" else 1
            panel = page.locator(f"#arch-side-{learned_side} .adaptive-decision")
            if panel.count():
                panel.locator("summary", has_text="Learned strategy decision").click()
                panel.scroll_into_view_if_needed()
                page.screenshot(path=str(ROOT / "docs/assets/phase6-learned-decision.png"))
        if errors:
            raise RuntimeError("\n".join(errors))
        browser.close()
    print("Captured genuine Phase 6 desktop/mobile comparisons")


if __name__ == "__main__":
    main()
