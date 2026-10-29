# N08 #317 localization-gate diagnostics

## Change and invariant

The physical scan's fail-closed localization check now includes the rejected sample's presence, validity, state/reason, observed and expected epoch, receipt age, configured maximum receipt age, source timestamp, and simulation timestamp in its error. The acceptance predicate and configured freshness limit are unchanged; this change only makes an early refusal attributable.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_preflight_scan`: 48 passed. New cases confirm missing, invalid, non-TRACKING, wrong-epoch, and stale records remain rejected, while a fresh TRACKING record in the expected epoch passes.
- `python3 tools/project_status.py`: Structure/design PASS.
- Python byte compilation using `/tmp/n08-pycache-317`, shell syntax, JSON parsing, and `git diff --check`: passed.

## Runtime result

The unchanged #316 z=0.5 m profile ran as `n08-cancel-highspeed-prescan-20261026-317`. It reached the second low-height yaw segment and stopped on a fresh same-epoch `normalized_cost_exceeded` health sample; see [#317 runtime evidence](n08-midheight-yaw-lockout-20261026-317.md). The exact predicate details were captured, and no threshold change is included.
