# N10.3/#375 spawn-profile mismatch

## Result

The frozen protocol specified `config/components/simulation/n10_long_range_spawn_minus8.json` (`x=-8 m`) but the actual run recorded `config/runtime.json` (`x=-6.5 m`). The launch command set the planner profile but omitted `D435I_SPAWN_CONFIG`. The run therefore does not qualify as execution of the frozen #375 protocol. Its run-local cylinder and box observation coordinates were derived from the intended -8 m spawn and are offset by 1.5 m from the actual odometry origin.

The task did send a goal and ran PX4 SITL. Gazebo acknowledged the dynamic box, and EGO published a replacement spline, but the action ended `goal_timeout` after about 360 wall seconds. Independent arrival evaluation found a minimum true position error of 1.392 m and zero qualifying dwell. The EGO log repeatedly reported that the current trajectory terminal point was occupied and skipped planning. With the actual -6.5 m spawn, the +16 m target aligns to about x=9.60 m world; the room wall inner face is x=9.925 m and EGO inflation is 0.731 m. That geometry is consistent with the upstream collision refusal, though #375 did not query the final goal cell.

The run had zero prohibited contact events. The actual inserted-box sampled clearance was 0.785 m, or 0.757 m after subtracting maximum observed inter-sample envelope motion; this is a sampled diagnostic only. The static `unit_cylinder_0` observer collected no frames. No numeric acceptance threshold changed.

## Safe stop

The flight runner landed and disarmed. Its readback and a separate 6 s PX4/bridge readback both reported `LANDED`, landed=true, armed=false, control disabled, the vehicle remained disarmed, and zero control samples. `bash tools/project.sh stop n10-20261027-375-gatefree-cylinder0-observation` completed; the container exited 0.

## Next

Rerun as #376 with both `D435I_PLANNER_CONFIG` and `D435I_SPAWN_CONFIG` explicitly set. The run-local driver will compare the loaded planner path and the effective spawn source, source hash, and six pose values against the freeze before sending a goal. N10 remains `in_progress`. See the [JSON detail](n10-live-obstacle-cylinder-spawn-mismatch-20261027-375.json).
