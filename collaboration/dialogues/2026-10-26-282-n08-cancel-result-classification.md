# N08 caller-cancel result classification (#282)

## Project task summary

Continue the user-authorized N08 Goal-completion task in the single-D435i simulation. Reuse N07's passed evidence without rerunning it. A normal EGO goal ends at its stop/hold; a return route requires a separate command and segment.

## User/repository constraints

- Preserve N08 acceptance criteria and every existing safety threshold.
- N05 admission, health, timing, unknown-space, mapping, and PX4 gates remain mandatory.
- Build, static tests, scans, or failed preflight attempts do not count as flight passes.
- Each cold run uses its own fresh N05 map and is left landed/disarmed.

## Findings and correction

- #281's support scan and N05 admission passed; its runtime manifest contained the expected installed launcher hash. The goal was sent and caller cancellation occurred inside the requested speed window: PX4 horizontal speed 0.04323 m/s, EGO reference speed 0.06092 m/s.
- Navigation published `MODE_STOP_HOLD` with reason `caller_cancel`. The runner compared the ROS action `outcome` field with the reason string. Correct values are `outcome="canceled"`, `reason="caller_cancel"`; the mismatch triggered safe Offboard disable and landing before the EGO replacement spline could be observed. The run is failed/incomplete, and does not establish stop behavior.
- Fixed the field comparison and added a regression test. The complete project suite passed 336 unit tests plus navigation-adapter integration. The new runner records cancel trigger/action-result details before checking the replacement stop spline.

## Current state and next action

N08 remains in progress. Start a new cold simulation and complete N05 scan/admission before rerunning the low-speed caller-cancel test. Continue until the stop spline, hold, measured braking, controlled comparisons, budget feedback, and frozen-version three-run ordinary-target exit all have evidence. Details are in [the #282 change record](../../progress/changes/2026-10-26-282-n08-cancel-result-classification.md).
