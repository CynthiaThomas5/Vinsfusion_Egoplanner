# N10.3/#422 — #415 fault-to-terminal audit

## Finding

The #415 native planner fault does not reach the required PX4 terminal state in the recorded session. The proximal chain is supported by run logs: the localization adapter latched `propagated_invalid_quaternion` at sim time 121.088 s; the last EGO occupancy update was at 121.080 s; EGO exceeded its native 0.400 s depth/odometry timeout at 121.516 s, aborted the active goal, and the bridge entered its landing path. The exact offending propagated quaternion and its VINS input cause were not captured, so the invalid quaternion's origin remains unknown.

The current bridge implementation explains why this path can remain pending:

- `px4_bridge_node.py` maps PX4 `DESCEND`, `AUTO_LAND`, and `AUTO_PRECLAND` into `px4_landing_active`.
- `control_state.py::_landing_command` stops sending another `NAV_LAND` request when that flag is true (or the LAND command has an accepted ACK).
- `control_state.py::step`, in `LANDING`, transitions to `LANDED` only when PX4 reports `landed=true` and `armed=false`. Otherwise it waits without a timeout or a separate non-terminal escalation path.

In #415, PX4 remains armed/failsafe in `DESCEND`, with local XY invalid, EV position/yaw fusion false, and `land_detected=false`. Thus the bridge's `LANDING` label is not proof of a completed landing. The current implementation has no evidence-backed bounded path for the observed `DESCEND`-without-land-detection state. This is an unresolved fault-path gap; no timeout, new health gate, or forced-disarm policy is selected by this audit.

## Latest read-only observations

- `r11` read-only ROS probe: 8 s; 63 bridge status, 14 PX4 status, 9 land-detection samples; zero terminal samples. Bridge remained `LANDING` and reported `control_enabled=true`; PX4 remained armed/failsafe `DESCEND`, XY invalid, EV fusion false, land detection false. No control-input message events were sampled, although publisher endpoints remained discoverable. The invalid PX4 XY estimate is not treated as physical truth.
- The bridge detail reported the last validated alignment pair was 1,690.2 wall seconds old and the current pair gap was 1,529.632 simulated seconds.
- A separate 2 s Gazebo truth observer recorded 450 poses with z between 0.3187 and 0.3275 m and 0.1066 m XY endpoint displacement. This is near-ground pose evidence only; it does not prove ground contact, landed detection, disarm, or safe-to-stop.
- Final `r12` read-only ROS probe: 6 s; 45 bridge status, 9 PX4 status, 5 land-detection samples; zero terminal/control-topic events. It remained armed/failsafe `DESCEND` and bridge `LANDING`; the last validated alignment pair was 1,799.9 wall seconds old.
- Exact artifacts and hashes are in the JSON report. The active runtime stack was not signaled and no control message was published by the probe.

## Required next sequence

1. Keep #415 supervised until native terminal state or new explicit authorization for one emergency disarm and controlled stop. The earlier one-time authorization was consumed at #391.
2. After closeout, preserve the final PX4/bridge state and raw run files. Fix the observer shutdown behavior that prevented final truth/contact reports.
3. Before changing landing logic, use preserved PX4/native logs and a new read-only integrity record containing the offending propagated quaternion, norm, stamp, and matching optimized/IMU samples to distinguish estimator corruption from adapter input/representation issues. Do not normalize or mask the input without that evidence.
4. Select a source-backed handling rule for `DESCEND` without valid local XY or land detection. Any implementation change must retain native PX4 preflight/fusion behavior and the existing no-runtime-acceptance-gate requirement; then add state-machine tests and one diagnostic calibration before freeze.
5. Continue the remaining N10.3 calibration only after safe closeout and an updated fixed runtime identity. Keep N15's two formal repetitions per fault class and N16's continuous 600 simulated seconds after N10 freeze.

## Scope

This is a read-only runtime/source audit. No runtime source or configuration, acceptance threshold, control policy, or flight task was changed. N10 remains `in_progress`; #415 does not count as successful fault-to-terminal calibration.
