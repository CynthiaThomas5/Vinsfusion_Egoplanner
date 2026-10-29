# N10.3/#375 protocol — cylinder observation with project health gates removed

#375 repeats the unchanged #371/#372/#373 diagnostic. Goal, world, spawn, planner profile, obstacle trigger, `unit_cylinder_0` observer, and acceptance thresholds remain unchanged. The current source/install fingerprint is `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7` (665 files); the 0054 patch and run-local tools are hash-bound in the freeze.

Required launch command:

```bash
D435I_PLANNER_CONFIG=config/components/mapping/n10_horizon5_speed080_calibration.json \
  bash tools/project.sh sim n10-20261027-375-gatefree-cylinder0-observation
```

The driver records localization status, source/receipt ages, depth/cloud/map observations, and bridge telemetry without the audited project-local VINS/depth health threshold refusals. Epoch/frame/time identity, PX4 native preflight/EV fusion, single bridge control owner, official EGO collision behavior, native input watchdogs, contact observation, and pre-goal graph/service checks remain. This is diagnostic preparation, not flight evidence or formal N10/N12 qualification.
