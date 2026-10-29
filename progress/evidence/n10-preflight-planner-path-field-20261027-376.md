# N10.3/#376 preflight failure — planner path field

The run-local driver stopped before starting flight observers or sending a goal because `planner_config_path` was absent at the top level of the prelaunch JSON. The actual launch manifest already showed the expected planner file and values; this was a preflight record-shape mismatch. The -8 m spawn source/hash/pose also matched.

An independent 6 s PX4/bridge readback reported DISABLED, landed, disarmed, control disabled, vehicle remained disarmed, and zero control samples. No `flight.json` or `flight-probe-ready` exists. The same stack is retained, disarmed, for a preflight-only retry. The corrected prelaunch record now has the top-level planner path and its SHA-256 is bound in the tool freeze; the driver verifies both before starting observers. No acceptance thresholds or runtime controls changed. See the [JSON record](n10-preflight-planner-path-field-20261027-376.json).
