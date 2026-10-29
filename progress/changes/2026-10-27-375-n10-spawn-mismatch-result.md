# N10.3/#375 — spawn identity mismatch result

## Result

The frozen protocol specified `config/components/simulation/n10_long_range_spawn_minus8.json` at x=-8 m, but `D435I_SPAWN_CONFIG` was omitted and the run loaded `config/runtime.json` at x=-6.5 m. The observer derived its local obstacle centers from the frozen -8 m input, so #375 is not counted as execution of that protocol.

The PX4 goal action timed out after 360.04 wall seconds with final estimated pose [14.3193, 0.0543, 1.0603] m and minimum independent truth goal error 1.392 m. The log repeatedly reports the upstream EGO terminal point in occupied space. The target mapped to world x≈9.602 m, about 0.323 m from the +X room inner face and inside the planner 0.731 m inflation; this explains the refusal geometrically, but remains an inference because #375 did not query the goal voxel. Prohibited contacts were zero. Actual-world sampled box clearance was 0.785 m (0.757 m after the measured inter-sample envelope allowance); it is not a continuous guarantee.

The run landed, disarmed and disabled bridge control. A separate 6 s PX4/bridge readback confirmed zero control samples; `project.sh stop` exited the container with code 0. No threshold changed.

## Next

Run #376 with explicit -8 m spawn and planner profiles, with driver checks for loaded profile path, spawn source hash, and all six pose values. See [evidence](../evidence/n10-live-obstacle-cylinder-spawn-mismatch-20261027-375.md). N10 remains `in_progress`.
