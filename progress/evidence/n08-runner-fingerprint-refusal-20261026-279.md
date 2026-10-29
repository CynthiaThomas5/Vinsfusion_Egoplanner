# #279 N08 runner fingerprint refusal before control

The full N05 support scan completed, the fixture was independently confirmed absent, N05 online/offline entry admission passed, and the 40 second read-only mission preflight passed. The N08 runner then refused before action setup because `runtime-contract.json` omitted `install/uav_navigation/lib/uav_navigation/navigation_supervisor`. The installed executable matched the pinned #276 build hash; the runtime manifest simply did not enumerate that launcher.

No `n08-trial-pre-enable-admission.json` was produced and the runner raised at the fingerprint guard before ROS action/enable setup. The generic `flight.json` is marked FAIL because no terminal runner record was written; that is a pre-control refusal, not a motion trial. A later fresh N05 read still reported the same identity, accepted raw envelope, DISABLED bridge, PX4 disarmed and landed. The run was safely stopped and no project processes remained.

The independent odometry evaluator also rejected the empty/partial failure record because its timestamps were not strictly increasing; this is secondary and provides no motion evidence. See the fingerprint fields and artifact hashes in the JSON report.
