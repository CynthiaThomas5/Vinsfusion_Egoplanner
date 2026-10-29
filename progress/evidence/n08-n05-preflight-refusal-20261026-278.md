# #278 N05 preflight refusal

Fresh navigation readiness passed, but the separate N05 raw-map entry gate correctly refused before any flight action. The refusal was `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`; the ground plane itself was valid.

The live and offline classifiers agreed. The snapshot had 14,751 raw free voxels; contact contained 436 unknown cells, and ascent/hold also contained unknown body-envelope cells. Occupied cells did not trigger the refusal. PX4 was disarmed, the bridge was DISABLED, and no control or goal was published. This is a preflight refusal, not a flight trial.

Artifacts: `artifacts/runs/n08-cancel-low-20261026-278/n05-current-area/`; raw map SHA256 is recorded in the JSON report.
