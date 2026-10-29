# N08 #319 runtime result

- #319 used the unchanged #312 high-altitude scan prefix and proposed a segmented neutral-pitch descent. It completed 12/35 stages, then same-epoch fresh localization locked during yaw return (normalized cost 1.007907; source age 44 ms; receipt age 0.000056 s).
- The run never returned to neutral yaw or reached the segmented descent; it gives no evidence for or against the dwell hypothesis. The initial same-run N05 online/offline pair agreed on `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`.
- No release gate, preflight, geometry, goal, control enable or flight occurred. Fixture removed/landed; separate 6 s readback confirmed DISABLED, disarmed/landed, zero control samples; container exit 0.
- #312 and #319 share the same movement prefix through the failing stage, but their localization outcomes differ. Next, compare the existing time-aligned VINS samples, features, solver costs, biases and health inputs before choosing another action. Keep every threshold unchanged and do not repeat #319.
- A mission, when reached, remains a single forward goal that ends at its target; return is a separate command.

Evidence: [#319 report](../../progress/evidence/n08-segmented-neutral-descent-yaw-lockout-20261026-319.md).
