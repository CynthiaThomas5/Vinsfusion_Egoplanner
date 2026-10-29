# #335 N10 evidence coverage

- User explicitly requested completion of N10; Goal completion mode remains active.
- N10.2 mapped N01–N09 evidence to GOAL A/F and later N11–N16 requirements; no testing or flight occurred.
- Preserve limited historical scopes. N02/#332 health causes remain unknown and original gates stay unchanged; failures remain fail-closed and never count as successful tasks.
- Old N05 known-free scans and N06 planner-only curves describe the previous policy. Current official_ego live semantics and N09 takeoffs are retained; formal obstacle flights remain N12–N14.
- Reuse N07 (no clock-path change), N08 only in measured low-speed range, and the three passed old N09 profile runs; preserve repeat03 failure.
- GOAL F is <=0.30 m, <=15 degrees and >=3 continuous simulation seconds. Existing 1 s dwell/wall-clock arrival window do not meet it; align in N10.4.
- Corrected #334 timeout interpretation: action goal timeout is sim-clock; outer client waits timeout+4 wall seconds; 75 s is only takeoff activation. RTF<1 can cause early client timeout.
- N10.3 measures long range/time, actual vector speed, map geometry/clearance basis and official-policy replanning. N10.4 implements one acceptance configuration/evaluator and complete runtime manifest; N10.7 restores a portable image archive.
- Next: N10.3 independent calibration.
- Evidence: `progress/evidence/n10-evidence-coverage-20261026-335.md` and `.json`.
