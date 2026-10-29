# N10.3 #380 braking repeat protocol

## Constraints

Continue N10 in Goal completion mode. Keep the 0.60–0.66 m/s interval as a PX4 sample trigger only, not as a flight speed cap or acceptance threshold. Do not restore project-added health gates. Preserve the frozen runtime and official behavior.

## Evidence basis

#378 and #379 were two successful same-runtime independent cold starts using identical planner, spawn, one-goal route and stop-band definition. Their PX4 horizontal trigger speeds were 0.600867/0.601259 m/s; stop-band entry times 4.844/4.880 simulated seconds; truth horizontal path lengths 1.376716/1.343935 m. The path-length difference was 0.032780 m. These are finite descriptive measurements, not a guarantee.

## Frozen #380 repeat

Third independent cold start. Exact same runtime source/install hash, horizon5/0.8/0.25 official_ego planner, [-8,0,0.3] spawn, +16m/+0.10m/+0.20rad goal, [0.60,0.66] m/s actual PX4 trigger, stop band and observers. No input variable or acceptance criterion changes.

## Status

Protocol and prelaunch hashes are frozen; SITL has not started and no goal has been sent. N10.3 remains incomplete; after this sample, synthesize the three-run braking range and continue other metric/support-scope evidence before N10.4.
