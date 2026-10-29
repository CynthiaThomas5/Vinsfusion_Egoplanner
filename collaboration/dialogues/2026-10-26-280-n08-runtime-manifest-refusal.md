# N08 runtime-manifest refusal and correction (#280)

## Project task summary

Continue the user-authorized Goal-completion work for N08 using the repository acceptance plan. Keep testing in the single-D435i simulation. Reuse already passed N07 evidence without retesting. A normal EGO target ends at its stop/hold; return is a separate command and second segment.

## Constraints retained

- Do not change N08 completion criteria or lower any threshold.
- Keep unknown-space, N05 admission, PX4 timing, localization health, velocity, tracking-tube, spatial-margin, and stop/landing gates.
- A preflight refusal, build, structure check, or scan does not count as a flight pass.
- Each cold run needs its own fresh map admission and safe landed/disarmed cleanup.

## Findings and decision

- #278 passed the read-only navigation preflight, then N05 correctly refused takeoff because the measured raw map had unknown voxels in the expanded aircraft envelope. No control or goal was published.
- #279 completed the documented 15-stage DISARMED support scan. Post-release online/offline N05 checks passed with stable identity. A delayed cleanup status prevented the scan wrapper from independently marking final safety, so a fresh read-only N05 check and Gazebo model-list query were obtained before continuing; both confirmed DISABLED/disarmed/landed and no support fixture. The simulator was retained until that state was resolved.
- #279 then passed mission preflight and fresh N05 admission, but the N08 runner stopped before action setup because `runtime-contract.json` omitted the installed `navigation_supervisor` launcher. The installed launcher hash matched #276 build evidence. No movement or cancellation trial occurred; the subsequent odometry error was a secondary evaluator failure on the incomplete record.
- Added the launcher to `tools/runtime_manifest.py` and a regression test. The focused test and direct workspace-hash check passed. No N08 flight result is claimed.

## Current state and next action

N08 remains in progress. Start a fresh simulation so the corrected runtime manifest is captured at startup, complete same-run N05 support scan/admission, then rerun the bounded 0.04–0.06 m/s motion-cancel stop/hold experiment. Continue through the remaining controlled comparisons, safety-budget feedback, and three independent cold-start ordinary-target passes. Evidence and exact run state are in [the #280 change record](../../progress/changes/2026-10-26-280-n08-runtime-manifest-refusal.md).
