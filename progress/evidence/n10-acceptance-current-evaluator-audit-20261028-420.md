# N10.4 #420 current acceptance-evaluator regression

## Verification

Revalidated the current offline N10 acceptance draft after its evaluator and configuration hashes changed since #394. No SITL was started and no runtime admission, cancellation, pause, or landing behavior was changed.

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tools.test_n10_acceptance tools.test_n10_clearance`: **30 tests passed**.
- Replayed the current evaluator on archived #381 and #385 using the source-bound shared calibration pair. Both reports show runtime identity and archived source hashes match.
- Draft config is revision 3, status `draft`; evaluator classified the runs without promoting provisional metrics to formal GOAL failures or passes.

## Archive results

| Run | Overall | Arrival | 10 s goal-motion translation RPE |
| --- | --- | --- | --- |
| #381 | `FAIL` | `FAIL` | 0.09586 m vs draft 0.05 m candidate |
| #385 | `INSUFFICIENT` | `PASS` | 0.09133 m vs draft 0.05 m candidate |

#385 active-hold RPE P95 was 0.02272 m, below the same draft candidate. Its motion-segment candidate breach remains visible in the metric row, while its overall status stays `INSUFFICIENT` because the config is draft and other required measures are missing. The two goal-motion exceedances are evidence that the candidate has not been demonstrated across this support range; no threshold was changed. Tracking-to-clearance acceptance remains unresolved, and missing observer identity reports remain `INSUFFICIENT`.

Machine-readable detail and source hashes: [JSON](n10-acceptance-current-evaluator-audit-20261028-420.json). Replays: `artifacts/runs/n10-20261027-389-archive-reuse/acceptance-replay-381-current.json` and `acceptance-replay-385-current.json`.
