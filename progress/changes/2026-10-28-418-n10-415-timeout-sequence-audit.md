# N10-20261028-418 — #415 timeout sequence audit

Dialogue summary: `collaboration/dialogues/2026-10-28-418-n10-415-timeout-sequence-audit.md`.

Read-only correlation of #415 log timestamps found `propagated_invalid_quaternion` lockout at sim 121.088 s, followed by a frozen EGO depth-pose sync count of 3,408 and last occupancy update at 121.080 s. At 121.516 s, the update age was 0.436 s against the unchanged native 0.400 s timeout; EGO aborted the active task with `planner_full_curve_depth_odom_timeout`.

This narrows the **proximate** failure path to localization integrity lockout, absent fresh valid depth/pose fusion, and native EGO timeout. It does not identify why VINS produced the invalid quaternion or establish a relation to compact trace encoding. No runtime/config/source was changed and no flight/control command was sent.

Evidence: `progress/evidence/n10-depth-timeout-sequence-20261028-415.md` and `.json`; source logs and hashes are listed there. N10 remains `in_progress`, pending safe closeout before any runtime change or subsequent run.
