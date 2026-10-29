# N10.3 #379 braking repeat 2 of 3

对话摘要：[2026-10-27 #379 protocol](../../collaboration/dialogues/2026-10-27-379-n10-speed060-repeat02-protocol.md)

- #378 produced the first valid same-runtime caller-cancel sample at PX4 horizontal speed 0.600867 m/s, with 4.844 simulated seconds to stop-band entry and 1.376716 m truth horizontal path.
- #379 is the second independent cold start under the exact same runtime, planner, spawn, goal, trigger window, stop band and observer protocol. No configuration or acceptance variable changes.
- Created a unique run id, protocol/prelaunch hashes, and run-local driver. The driver inherits the verified ROS setup and runtime-manifest preflight fixes from #378.
- Validation before SITL: driver bash -n; protocol/prelaunch python3 -m json.tool; frozen input hash checks; git diff --check; python3 tools/project_status.py.
- Goal not yet sent. N10 remains in_progress.
