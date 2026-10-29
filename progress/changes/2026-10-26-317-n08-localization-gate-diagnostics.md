# #317 N08 localization-gate diagnostics

## Change

Added a pure localization-gate diagnostic helper and included its observed fields in the existing preflight-scan refusal message. The rejection criteria and maximum receipt age are unchanged. Added regression cases for missing, invalid, non-TRACKING, epoch-mismatched, stale, and valid/fresh TRACKING status samples.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_preflight_scan`: 48 passed.
- `python3 tools/project_status.py`: Structure/design PASS.
- Python compile check with `PYTHONPYCACHEPREFIX=/tmp/n08-pycache-317`, shell syntax, JSON parsing, and `git diff --check`: passed.

## Runtime

The unchanged #316 mid-height scan profile ran cold-start as #317. The detailed error identified a fresh, same-epoch localization sample in LOST state due to `normalized_cost_exceeded`; the failure is not stale data or an epoch mismatch. See [#317 run report](../evidence/n08-midheight-yaw-lockout-20261026-317.md). The diagnostic change did not alter scan behavior or health thresholds.

Related dialogue: [#317 diagnostics](../../collaboration/dialogues/2026-10-26-317-n08-localization-gate-diagnostics.md).
