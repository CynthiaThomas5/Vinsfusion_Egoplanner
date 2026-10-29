# N10-20261028-420 — current acceptance evaluator regression

Dialogue summary: `collaboration/dialogues/2026-10-28-420-n10-acceptance-current-evaluator-audit.md`.

The active stack was confirmed separate from the offline evaluator. The current acceptance configuration and evaluator hashes differed from #394, so reran targeted acceptance/clearance tests and source-bound archive replays of #381/#385. Thirty tests passed. Both replays matched run identity and source hashes. #381 remains a direct `FAIL`; #385 remains `INSUFFICIENT`, with arrival `PASS` but 10 s goal-motion translation RPE P95 0.09133 m above the draft 0.05 m candidate. No threshold or runtime gate changed.

Evidence: `progress/evidence/n10-acceptance-current-evaluator-audit-20261028-420.md` and `.json`; replay outputs are under `artifacts/runs/n10-20261027-389-archive-reuse/`. N10.4 draft evaluator mechanics are revalidated; N10.3 calibration remains incomplete and prevents freeze.
