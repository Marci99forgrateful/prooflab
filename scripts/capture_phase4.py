"""Capture genuine static Search Architecture Explorer views from a local server."""

from playwright.sync_api import sync_playwright

from prooflab.lean import ROOT

out = ROOT / "docs/assets"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"])
    page = b.new_page(viewport={"width": 1600, "height": 1050})
    page.goto("http://127.0.0.1:8000/#architecture", wait_until="networkidle")
    page.wait_for_selector("#arch-side-1 .arch-state-title")
    for ident, step, name in [
        ("p4_cubic_pair", "6", "phase4-explorer"),
        ("p4_contra_disj", "9", "phase4-regression"),
    ]:
        page.locator("#arch-task").select_option(ident)
        page.wait_for_function(
            '(ident) => document.querySelector("#arch-statement").textContent.includes('
            'ident === "p4_cubic_pair" ? "^3" : "¬")',
            arg=ident,
        )
        page.wait_for_timeout(800)
        page.locator("#arch-step").fill(step)
        page.screenshot(path=str(out / f"{name}.png"), full_page=True)
    page.locator("#arch-side-1 .arch-whole").click()
    page.locator("#arch-side-1 .arch-fit").click()
    page.screenshot(path=str(out / "phase4-complete-tree.png"), full_page=True)
    page.locator(".arch-overview summary").click()
    page.screenshot(path=str(out / "phase4-measured-results.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(out / "phase4-mobile.png"), full_page=True)
    print("Captured five actual research-interface screenshots")
    b.close()
