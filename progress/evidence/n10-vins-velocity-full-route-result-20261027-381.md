# N10.3/#381 raw VINS velocity and long-route result

## Result

The single-D435i PX4 SITL diagnostic completed with action success, independent position/yaw dwell, a 600 simulated-second active hold, zero prohibited contacts, and independent landed/disarmed/control-disabled/zero-control readback. This is calibration evidence, not formal N10 or N11–N16 qualification.

- Run: `n10-20261027-381-vins-velocity-full-route`; runtime contract `547082a4538a871dd3c3b9b26c0f6b45369fa18bf1b73a8d93f219ef3e537cce` (666 files).
- Planner: `config/components/mapping/n10_horizon5_speed080_calibration.json`; spawn profile loaded at `(-8, 0, 0.3, 0, 0, 0)`.
- The only runtime difference from #376 was read-only capture of raw VINS `twist.linear`. No controller, PX4, planner, goal, collision policy, geometry, speed parameter or runtime gate changed.
- Initial PX4 preflight and official_ego takeoff admission passed; the goal graph had one publisher and one subscriber.
- The +16 m / +0.10 m / +0.20 rad action succeeded. Offline fixed-SE(3) truth evaluation found a continuous simultaneous `position ≤0.30 m` and `yaw ≤15°` dwell of `3.055 wall s` (minimum 3.0 s). Within this window, max position error was `0.298 m`; max yaw error was `11.89°`.
- The post-goal active hold completed 600 simulated seconds (784.922 wall seconds; RTF 0.764). No control goal was sent during this hold.
- All six required observers covered the terminal flight record. Contact evaluation passed with zero prohibited contacts.
- Independent postflight readback confirmed `LANDED`, disarmed, control disabled and zero control samples; safe-to-stop was true. The container was stopped via `tools/project.sh stop` with exit 0. Bridge reason `px4_preflight_failed` and PX4 `pre_flight_checks_pass=false` were sampled after landing/disarm; initial preflight had passed, so this is terminal readiness rather than an initial-preflight failure.

## Raw VINS, speed and tracking

Pose errors use one prestream rigid alignment, scale fixed to 1, with no flight-path fit or segment re-alignment. Coverage spans `673.596 simulated seconds` and `27.650 m` of truth path. All 10206 raw-velocity samples paired with truth; raw maximum source gap was `0.068 s` and truth maximum gap `0.020 s`.

| Window | Position error P95 / max | Absolute yaw error P95 / max | Raw velocity error P95 / max |
| --- | ---: | ---: | ---: |
| Goal motion + arrival dwell (45.9 sim s) | 0.117 / 0.119 m | 1.28 / 1.35° | 0.0282 / 0.0686 m/s |
| Exact 600 sim s active hold | 0.439 / 0.458 m | 6.59 / 6.87° | 0.0070 / 0.0261 m/s |
| PRESTREAM to LANDED (673.6 sim s) | 0.439 / 0.458 m | 6.59 / 6.87° | 0.0105 / 0.2971 m/s |

During the exact 600 s hold, independent truth position relative to the commanded goal had P95/max 0.447/0.456 m; it first exceeded the 0.30 m goal sphere 226.096 simulated seconds after action completion. This measures long-term drift during hold; the hold remained active for the full 600 s.

The full-window velocity maximum includes landing. The segmented report separates the completed 600 s hold (velocity error max `0.0261 m/s`) from the 5.352 s landing interval (max `0.2971 m/s`); the frozen original report is retained unchanged.

Full-run 10 s RPE: translation RMSE/P95/max `0.0185/0.0417/0.0998 m`; rotation `0.201/0.300/0.496°`. All 1/5/10 s RPE pairs were supported.

EGO reference-to-truth tracking error was P95 `0.560 m`, max `1.105 m`. The configured `max_vel=0.8 m/s` is per axis: this run observed EGO-reference vector peak `0.678 m/s` and PX4 vector peak `0.609 m/s`; these are route measurements, not global speed guarantees.

## Dynamic obstacle and clearance

The box was acknowledged `12.004 simulated seconds` after goal start. A replacement spline appeared `0.536 simulated seconds` after creation. The sampled pre-injection centerline distance to the box was `0.067 m`; the first replacement spline's sampled centerline distance was `1.451 m`. One receding-horizon run does not establish a general replan deadline.

All three read-only 0.25 m raw-map queries around the box returned `unknown` (112 unknown, 48 free, 0 occupied each); eight occupied-cloud ROI observations were recorded. The official EGO inflated-occupied collision path stayed active, without adding a project raw-free whole-curve rejection.

The whole sampled route's envelope clearance was `0.280 m`, reduced by observed inter-sample motion to `0.262 m`. For the box alone, sampled clearance was `0.856 m`, adjusted to `0.839 m`. These are offline sampled measurements, not a continuous-dynamics certificate.

Map source-age max was `0.160 sim s`; occupancy age max `0.108 s`. Normalized-cost P95/max were `2.420/2.723`; the historical 1.0 reference was exceeded with no project lockout and no invalid localization status sample. Quality and timing remain diagnostic observations.

## Limits and next action

The full-run fixed-alignment absolute position error was P95/max `0.439/0.458 m`; the exact hold window was P95/max `0.439/0.458 m`, while short-window RPE stayed smaller. The arrival dwell exceeded the 3 s floor by only `0.055 s` in this sample. Raw velocity has one full-route sample, and clearance/replanning remain single-run diagnostics.

This closes the raw-velocity measurement subtask. N10.3 still needs the cross-evidence metric-support matrix, provisional quantitative rationale and explicit applicability boundary. N10 remains `in_progress`.

Detailed inputs and hashes are in the JSON companion. The run archive is `../../artifacts/runs/n10-20261027-381-vins-velocity-full-route/`.
