# N10.3 #380 braking repeat 3 of 3

对话摘要：[2026-10-27 #380 protocol](../../collaboration/dialogues/2026-10-27-380-n10-speed060-repeat03-protocol.md)

- #378/#379 are two complete independent same-runtime samples. Actual PX4 horizontal triggers: 0.600867/0.601259 m/s; truth horizontal paths to stop-band entry: 1.376716/1.343935 m; stop-band entry: 4.844/4.880 simulated seconds.
- #380 freezes repeat 3/3 under a fresh PX4/Gazebo/VINS cold start. Runtime, planner, spawn, goal, trigger window, observers and stop band are identical. No parameter or acceptance criterion changes.
- Protocol, prelaunch, tool hashes, and run-local driver are saved in the listed evidence and prepared directories. The driver includes previously verified ROS setup and runtime-manifest initialization handling.
- Validation before SITL: bash -n on driver; python3 -m json.tool on protocol/prelaunch/milestone JSON; frozen SHA checks; git diff --check; python3 tools/project_status.py.
- #380 goal not yet sent. N10 remains in_progress.
