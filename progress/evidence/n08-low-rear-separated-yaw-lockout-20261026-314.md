# N08 #314: low-rear separated pitch/yaw scan refusal

## Scope

Cold-start unarmed whole-airframe support scan only. This run was intended to determine whether the #313 localization lockout came from combined pitch/yaw motion. It did not request a mission goal, enable PX4 control, or perform flight.

## Result

The scan completed 14 of 19 stages, then stopped with `normalized_cost_exceeded` at 1.0025576068. Correction to the original #314 profile description: stage 13 was **not** a pitch-only move. It simultaneously moved yaw from 0 toward −π/2 and pitch from 0 toward −0.35 rad; this stage completed with maximum observed normalized cost 0.880538. Stage 14 then held pitch at −0.35 rad and continued yaw from −π/2 toward −π at z≈0. Localization crossed its 1.0 health threshold partway through stage 14, near yaw −2.17 rad. The run therefore does not isolate yaw-only from pitch-only motion. It establishes only that the first combined 90° turn completed and the following fixed-pitch 90° turn did not.

The scan's initial N05 snapshot refused `ground_plane_insufficient_raw_occupied_voxels`. Because the support scan stopped before fixture release, same-identity post-release online/offline N05 checks, the read-only preflight, N08 forward geometry, and any mission were not run. There is no N08 flight result from this run.

## Safe end state

The fixture runner verified detachment, removal of the fixture model, and landed state. A separate six-second PX4/bridge readback reported bridge `DISABLED`, `armed=false`, `landed=true`, `vehicle_remained_disarmed=true`, and zero samples on offboard-control-mode, trajectory-setpoint, and vehicle-command inputs. The run container was stopped with `tools/project.sh stop`; it exited 0. No goal or enable command was issued.

## Evidence

- Run: `artifacts/runs/n08-cancel-highspeed-prescan-20261026-314/`
- Summary: `fixture-result.json`; stage and pose trace: `fixture-stages.json`, `fixture-trace.jsonl`
- Independent post-scan readback: `post-scan-independent-live-readback.json`
- Fixture model inventory: `post-scan-gz-model-list.txt`
- Profile static report: [#314 profile](n08-low-rear-view-separated-pitch-profile-20261026-314.md)

## Next discriminating action

Keep the existing descent and low-rear scan, but perform both yaw turns at neutral pitch. At the rear-facing stationary pose, change pitch alone, hold the view, restore neutral pitch, then return yaw in neutral pitch. This tests whether low-height yaw remains viable without the downward camera pitch present. Preserve all health, map, and spatial thresholds. If the scan completes, continue through the same-identity post-release admission gates before considering a one-way forward EGO cancellation run.
