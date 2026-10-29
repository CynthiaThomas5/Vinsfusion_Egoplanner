# N09 official-policy PX4 qualification (#332)

**Status: N09 limited exit passed.** Three independent cold starts passed under the official FAST Lab policy and one failed attempt is preserved separately. This is a single-D435i PX4/Gazebo run set; no support fixture or rear camera was used. Passing runs are repeat01, repeat02 and repeat04; repeat03 does not count.

## Frozen identity and already completed checks

- Active policy: `official_ego`; frozen runtime SHA256: `6b95d5fe48ea17f41649947547ccab4bf0798e9907a565dbb2dfd65cf0579f30`.
- Goal profile: `config/components/navigation/n09_3d_waypoint_goal.json`, SHA256 `04d2287d22481257ab59cd983fa439b68e130f210d111f938a2f2fa89bd92012`; one 3D waypoint at approximately +0.4 m forward, +0.1 m up, with +0.2 rad yaw.
- The #331 implementation passed the 17-package ROS build, full 397-test suite including the official-policy ROS action integration, and complete pinned dependency patch replay. Logs and pinned upstream sources are under `artifacts/runs/n09-official-policy-331/`.
- The corrected live official map-policy probe passed raw-unknown retention / planning allowance, inflated occupied refusal, out-of-map refusal, and old-epoch refusal. See `artifacts/runs/n09-official-331-pilot01/official-map-policy-probe-corrected.json`. Pilot01 is policy-semantic evidence only and is not one of these three runs because its runtime SHA differs.

## PX4 cold-start runs

| Run | Outcome | Independent 3D displacement | Height change | Yaw change | Contact / terminal evidence |
| --- | --- | ---: | ---: | ---: | --- |
| `n09-official-331-repeat01` | N09 evaluator passed all 11 checks | 0.41072 m | 0.10075 m | 0.19257 rad | 0 prohibited contacts; ground landing observed; independent LANDED/disarmed readback and 6 s with no control setpoints |
| `n09-official-331-repeat02` | N09 evaluator passed all 11 checks | 0.40999 m | 0.10006 m | 0.19215 rad | 0 prohibited contacts; ground landing observed; independent LANDED/disarmed readback and 6 s with no control setpoints |
| `n09-official-331-repeat03` | **Failed; not counted** | Partial motion only; no verified arrival | Takeoff completed | Goal yaw not reached | No prohibited contacts; PX4/bridge independently read LANDED/disarmed and emitted no offboard/setpoint messages in the terminal readback |
| `n09-official-331-repeat04` | N09 evaluator passed all 11 checks | 0.40803 m | 0.09944 m | 0.19634 rad | 0 prohibited contacts; ground landing observed; independent LANDED/disarmed readback and 6 s with no control setpoints |

Repeat01, repeat02 and repeat04 have distinct PX4 cold-start runs, VINS epochs, map IDs, and goal IDs, with the same frozen runtime and goal profile. All three retained localization/odometry freshness within the N09 limits and map ages below the 0.4 s limit through landing. Repeat03 used the same frozen runtime/profile but failed before arrival and remains excluded from the 3/3 success count.

## Repeat03 failure analysis

The goal was sent and PX4 reached `ACTIVE`. At VINS source time 79.036 s, one estimator telemetry frame reported `normalized_cost=1.1006559707840762` against the unchanged 1.0 health limit. The preceding frame was 0.459839 and the following frame was 0.488783. Feature counts remained 180 input, 155 stereo, and 90 long tracks; the solver reported usable and finite state, but termination type 1. The residual breakdown for the outlier was dominated by visual cost (2478.424 across 4020 residual components), with IMU cost 23.636 and marginalization cost 73.469. This supports a one-frame visual residual spike; it does not identify why that image/estimate pair disagreed.

There was no ROS clock regression, and source/receipt streams remained timely before the health lockout. The bridge entered `LANDING` with reason `normalized_cost_exceeded`; PX4 then landed/disarmed. The localization health threshold and fail-closed behavior were not changed. The navigation action did not succeed, so the independent arrival evaluator correctly cannot credit the run; its wrapper reported that the failed run had no truth sample bracketing a goal-completion timestamp. The post-mission live map-refusal probe also could not complete after localization had locked out.

This failure is not evidence against the official unknown-space policy, and it is not counted as arrival. It remains a separate VINS-health failure observation. The visible temporal association with the final yaw turn is not enough to claim that yaw caused the residual spike.

## N09 exit and handoff

The N09 limited exit is complete: 3/3 successful independent cold starts, all 11 independent mission checks in each passing run, distinct VINS/map/goal identities, no prohibited contacts, and independent landed/disarmed readback. Repeat03 remains a failed health-lockout observation and is not hidden or counted. The health threshold was unchanged. N10 is the next dependency in the project queue, but this authorization covered N09 only, so no N10 work is started here.

Per-run artifacts: `artifacts/runs/n09-official-331-repeat01/`, `repeat02/`, `repeat03/`, and `repeat04/`. The failed run's native `flight.json`, `arrival-evaluation.json`, `n08-localization-source-timeline.json`, VINS telemetry, contact evaluation, and independent terminal readback are retained there.
