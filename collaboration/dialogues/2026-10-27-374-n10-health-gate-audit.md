# N10 Goal completion — remaining project health gates

## Scope

Continue N10.3 and follow the user instruction to inspect project-owned protective gates before removing them.

## Confirmed and changed

- N10 admission/navigation/bridge still treated project `LocalizationStatus.valid/TRACKING` as a refusal/abort signal after numeric age and quality gates were removed. That state is now observational; same-epoch goal operation is allowed.
- The mapping path still required the custom DepthHealth topic and at least 16 sampled valid pixels. The standard VIO/EGO and debug-truth launch no longer activates that gate; structurally valid depth is forwarded and invalid pixels stay unknown.
- Epoch/map/frame/time checks, PX4 native preflight and EV fusion, one bridge control owner, and upstream EGO collision/input behavior remain.
- Build: 17 ROS packages passed. Tests: 415 unit tests and both ROS integration probes passed.
- #374 was not launched. #375 is frozen with the updated runtime identity and correct planner profile environment.

## Pending

Run #375 and determine whether the actual #371 contact cylinder reached depth/occupied/map inputs and how the dynamic replan behaved. N10 remains `in_progress`.
