# Visualization

The browser reads actual per-attempt trace JSON. One root is the native initial
Lean state. Every other node is an accepted, rejected, interrupted or solved
tactic attempt. Edges refer to recorded parent IDs. No decorative search
branches are invented.

The default **Recorded replay** mode is entirely static and can be hosted on
GitHub Pages. Play, pause, single step, scrub and speed control progressively
reveal the recorded computation. Green path marking uses the independently
verified final path and is explicitly retrospective replay, not a prediction
made during computation.

In the local app, **Use live search** starts a new Lean computation. The UI
shows progress text, then displays its completed authentic trace for inspection
and playback. **Live candidate-by-candidate streaming is not implemented**.
The comparison screen uses recorded runs of the identical statement and shows
both policies, effort, time and exact proof scripts.

Select a node by pointer or Enter to inspect tactic, local hypotheses, remaining
goals and error. For a rejected attempt, the inspector explicitly shows the
unchanged parent's actual state. Zoom/pan, fit, SVG export, proof copy and Lean
artifact download are available. Colors are complemented by symbols and labels.

Main rendering is capped at 320 nodes; comparison at 220. All raw data remains
in downloadable research trace files. Larger-search clustering and fully
incremental layout are future work. KaTeX and its fonts are bundled locally;
there is no CDN requirement. Light/dark themes and desktop/tablet/mobile layouts
are covered by actual Chromium tests and screenshots.

`scripts/capture_demo.py` captures real application screenshots and a short GIF
of authentic recorded playback. These are evidence of the running interface,
not generated mockup images.
