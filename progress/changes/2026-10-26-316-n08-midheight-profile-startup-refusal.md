# #316 N08 mid-height profile startup refusal

## Result

The cold-start helper aborted before issuing any scan stage command. The error named a localization validity/identity change, while its final record was valid and low-cost; the rejected-time predicate was not stored. The run therefore did not test the altitude variable in the profile.

Initial N05 online/offline refused the same current map for `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`. Fixture detachment/removal and landed state passed; independent six-second readback confirmed bridge disabled, PX4 disarmed/landed, and zero control samples. Only #316 was stopped; container exit 0. No goal or enable command was issued.

See [#316 startup refusal](../evidence/n08-midheight-profile-startup-refusal-20261026-316.md) and raw artifacts in `artifacts/runs/n08-cancel-highspeed-prescan-20261026-316/`.

## Next

Instrument the existing localization fail-closed check to report state, validity, expected/observed epoch, receipt age, and configured freshness limit. Preserve the exact rejection rule, add focused tests, then rerun the same z=0.5 m profile cold-start. Do not interpret #316 as altitude evidence.

Related dialogue: [#316 startup refusal](../../collaboration/dialogues/2026-10-26-316-n08-midheight-profile-startup-refusal.md).
