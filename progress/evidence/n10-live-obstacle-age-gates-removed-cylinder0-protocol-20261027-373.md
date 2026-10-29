# N10.3/#373 protocol — repeat #372 with the frozen planner profile loaded

#372 ended before goal submission because the runtime was launched without the required `D435I_PLANNER_CONFIG` override. Its frozen driver correctly rejected the default planner values. #373 preserves the same world, spawn, goal, planner values, dynamic obstacle and trigger, cylinder observer, age-gate removals, and acceptance thresholds.

The required launch command is:

```bash
D435I_PLANNER_CONFIG=config/components/mapping/n10_horizon5_speed080_calibration.json \
  bash tools/project.sh sim n10-20261027-373-gatefree-cylinder0-observation
```

Before the driver can send a goal it will recheck the runtime/tool hashes, loaded EGO parameters, ROS graph, Gazebo and hidden action-cancel services, contact sensors, and landed/disarmed bridge state. The run remains diagnostic, not formal N10/N12 qualification. After the mission, the independent readback must confirm landed, disarmed, control disabled, and zero control samples before the project container is stopped. Machine-readable protocol: [JSON](n10-live-obstacle-age-gates-removed-cylinder0-protocol-20261027-373.json).
