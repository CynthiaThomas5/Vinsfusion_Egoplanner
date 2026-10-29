# N08 #316 startup refusal

- The planned z=0.5 m yaw profile did not begin: 0/23 stages completed, and the helper raised its localization validity/identity error before the first stage command.
- The final captured localization was TRACKING/valid with normalized cost 0.084701, so the actual failing-time predicate is not known. This run says nothing about whether the altitude change helps.
- The same-run initial N05 online/offline check agreed and refused `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`.
- Fixture detached and was removed; landed and disarmed states were independently verified for six seconds with zero control samples. Only #316 was stopped, exit 0.
- Next #317 adds diagnostic detail to the unchanged fail-closed check and repeats the same profile cold-start. No thresholds will change.
