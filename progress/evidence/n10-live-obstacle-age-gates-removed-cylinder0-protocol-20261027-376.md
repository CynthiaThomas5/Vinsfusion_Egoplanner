# N10.3/#376 protocol — same cylinder/dynamic-box diagnostic at frozen spawn

#375 loaded the default x=-6.5 m spawn although #371 and this protocol specify x=-8 m. #376 corrects that omitted launch override and adds an identity check for both planner and spawn before sending a goal. The goal, world, EGO profile, dynamic-box trigger, observer, thresholds, and official collision semantics remain fixed.

Required launch command:

```bash
D435I_PLANNER_CONFIG=config/components/mapping/n10_horizon5_speed080_calibration.json \
D435I_SPAWN_CONFIG=config/components/simulation/n10_long_range_spawn_minus8.json \
bash tools/project.sh sim n10-20261027-376-gatefree-cylinder0-observation
```

The run-local driver checks the current runtime/tool/protocol hashes, exact loaded planner path and values, plus the spawn profile source path/hash/all six pose values before flight. It then observes D435i depth/color, EGO occupied cloud, same-identity map queries, action/trajectory behavior, contact sensors and independent safe-stop state. This remains a diagnostic, not a formal N10/N12 qualification.
