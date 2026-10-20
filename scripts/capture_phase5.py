"""Photograph the actual integrated replay UI, never synthesized proof imagery."""

from __future__ import annotations

import argparse
import json
import os
import shutil

from playwright.sync_api import expect, sync_playwright

from prooflab.lean import ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    output = ROOT / "docs/assets"
    index = json.loads((ROOT / "web/public/phase5/explorer.json").read_text())
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.environ.get("PROOFLAB_CHROMIUM") or shutil.which("chromium"),
            headless=True,
            args=["--no-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1600, "height": 1100}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(args.url, wait_until="networkidle")
        page.locator('[data-view="architecture"]').click()
        expect(page.locator("#arch-side-1 .arch-state-title")).to_contain_text("State 0")
        page.locator("#arch-dataset").select_option("phase5")
        expect(page.locator('#arch-task option[value="p5_product_graph"]')).to_have_count(1)
        page.locator("#arch-task").select_option("p5_product_graph")
        expect(page.locator("#arch-statement")).to_contain_text("α × β")
        expect(page.locator("#arch-side-1 .pill")).to_have_text("verified")
        page.locator("#arch-side-1 .premise-family").select_option("witness")
        page.locator("#arch-side-1 .premise-selected").check()
        page.locator("#arch-side-1 .premise-table summary").first.click()
        page.locator("#arch-side-1").screenshot(path=str(output / "phase5-native-witness.png"))
        page.evaluate(
            "window.scrollTo(0,document.querySelector('.arch-comparison').getBoundingClientRect().top+scrollY-12)"
        )
        page.screenshot(path=str(output / "phase5-tree-comparison.png"))
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#arch-side-1 .arch-premises").scroll_into_view_if_needed()
        page.screenshot(path=str(output / "phase5-mobile.png"))
        page.set_viewport_size({"width": 1600, "height": 1100})
        case = next(e for e in index["examples"] if e["title"] == "Typed generator regression")
        page.locator("#arch-task").select_option(case["task_id"])
        page.locator("#arch-policy-a").select_option(case["left"])
        page.locator("#arch-policy-b").select_option(case["right"])
        expect(page.locator("#arch-side-0 h2")).to_have_text(index["policy_names"][case["left"]])
        expect(page.locator("#arch-side-1 h2")).to_have_text(index["policy_names"][case["right"]])
        expect(page.locator("#arch-side-0 .pill")).to_have_text("not_found_within_budget")
        expect(page.locator("#arch-side-1 .pill")).to_have_text("verified")
        page.evaluate(
            "window.scrollTo(0,document.querySelector('.arch-comparison').getBoundingClientRect().top+scrollY-12)"
        )
        page.screenshot(path=str(output / "phase5-regression.png"))
        if errors:
            raise RuntimeError("\n".join(errors))
        browser.close()
    print("Captured four actual desktop/mobile proof-search views")


if __name__ == "__main__":
    main()
