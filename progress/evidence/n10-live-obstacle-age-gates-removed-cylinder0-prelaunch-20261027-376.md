# N10.3/#376 prelaunch identity

Runtime contract: `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7` (665 files). Protocol SHA-256: `8920d26b7cddbcb0976e6bf73db872f7d71a49dbd555a07ef52be56958dc5d27`. Required planner and spawn identities are recorded in the [JSON prelaunch record](n10-live-obstacle-age-gates-removed-cylinder0-prelaunch-20261027-376.json) and run-local [freeze](../../artifacts/n10-prepared/n10-20261027-376-gatefree-cylinder0-observation/n10-tool-freeze.json).

Effective spawn must be `config/components/simulation/n10_long_range_spawn_minus8.json`, pose `[-8,0,0.3,0,0,0]`. Planner must be `config/components/mapping/n10_horizon5_speed080_calibration.json` (0.8 m/s, 0.25 m/s², 5 m horizon, official_ego). The driver refuses only a mismatch in these frozen run identities; no project-local health threshold was reintroduced. No #376 container or goal has started.
