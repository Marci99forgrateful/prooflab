# Third-party software

ProofLab's original code is Apache-2.0 (see LICENSE). Dependencies are installed
separately; their source and original notices remain in their distributions.

| Dependency | Role | License / source |
|---|---|---|
| Lean 4.24.0 | Elaborator and kernel | Apache-2.0; https://github.com/leanprover/lean4 |
| Mathlib | Mathematics and tactics | Apache-2.0; https://github.com/leanprover-community/mathlib4 |
| Batteries, Aesop, Qq | Lean dependencies | Apache-2.0; pinned in lake-manifest.json |
| KaTeX 0.16.22 | Browser mathematical typesetting and local fonts | MIT; https://github.com/KaTeX/KaTeX |
| Vite | Frontend bundling | MIT; https://github.com/vitejs/vite |
| FastAPI, Pydantic | Local API and schemas | MIT |
| Uvicorn | Local HTTP server | BSD-3-Clause |
| Pytest, Ruff, Mypy | Development validation | MIT |
| Playwright | Browser tests and captures | Apache-2.0 |
| Matplotlib | Research figures | Matplotlib license (PSF based) |

No third-party theorem source is copied into the search engine. The lemma index
references original declaration names and defining modules. Static distribution
includes KaTeX; its license is preserved as `web/public/katex-LICENSE.txt`.
The browser demo contains real recorded proof traces, not third-party proof text
copied as task-specific answers.
