# HW04 execution summary — 2026-11-02

- User requested all HW04 exits from `docs/hardware-agent-workbook.md`, reusing CURRENT and existing HW01–03 evidence. Scope remains HW04 only; no mapping, PX4, Gazebo, SITL, control, or flight.
- HW03 provisional real-rig/session identity was reused to create fresh per-run epochs. Hardware localization uses `use_sim_time=false`, system ROS time for source age, and monotonic receipt age.
- A default VINS UDP receiver accumulated kernel receive-buffer errors. Applying a 4 MiB receive-buffer profile to the VINS participant, with Nano `net.core.rmem_max` temporarily set to 8 MiB, produced a five-minute stationary valid run with no increase in UDP `RcvbufErrors`.
- VINS stop invalidation and fresh-epoch succession were observed. Sensor and localization processes were stopped and the temporary kernel value restored.
- The operator did not start the requested physical route; the camera trace remained stationary. HW04 remains incomplete until the 2–3 minute translation/lift/yaw/return route is captured. Native VINS queue high-water metrics were absent from the installed binary and remain a limitation.
