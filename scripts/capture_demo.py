"""Capture genuine application screenshots and an authentic replay GIF."""

import argparse
import shutil
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    destination = ROOT / "docs/assets"
    destination.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=shutil.which("chromium"), headless=True, args=["--no-sandbox"]
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1120}, device_scale_factor=1)
        page.goto(args.url, wait_until="networkidle")
        page.wait_for_selector(".tree-node")
        page.screenshot(path=str(destination / "proof-explorer.png"), full_page=True)
        page.locator("#speed").select_option("800")
        page.locator("#run-button").click()
        time.sleep(1.7)
        page.screenshot(path=str(destination / "active-search.png"), full_page=True)
        page.locator("#play-toggle").click()
        frames = []
        count = int(page.locator("#timeline").get_attribute("max"))
        for step in range(1, count + 1):
            page.locator("#timeline").fill(str(step))
            path = destination / f".frame-{step}.png"
            page.locator(".workspace-grid").screenshot(path=str(path))
            frames.append(Image.open(path).convert("RGB"))
            path.unlink()
        frames[0].save(
            destination / "proof-search.gif",
            save_all=True,
            append_images=frames[1:],
            duration=650,
            loop=0,
        )
        page.locator('[data-view="compare"]').click()
        page.wait_for_selector("#comparison-grid svg")
        page.screenshot(path=str(destination / "algorithm-comparison.png"), full_page=True)
        page.locator('[data-view="benchmarks"]').click()
        page.screenshot(path=str(destination / "benchmarks.png"), full_page=True)
        page.locator('[data-view="lab"]').click()
        page.locator("#theme-toggle").click()
        page.screenshot(path=str(destination / "dark-theme.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(destination / "mobile.png"), full_page=True)
        browser.close()
    print("Captured authentic screenshots and replay GIF")


if __name__ == "__main__":
    main()
