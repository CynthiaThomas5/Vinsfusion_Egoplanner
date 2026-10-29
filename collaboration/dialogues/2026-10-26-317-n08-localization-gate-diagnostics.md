# N08 #317 localization diagnostics

- #316 aborted before its first stage. The final localization record was valid, but the failing sample was not included in the error, so that run could not test its z=0.5 m profile.
- Added diagnostics for message presence, validity, state/reason, observed/expected epoch, receipt age, allowed age, source stamp, and simulation time. The health predicate and thresholds remain unchanged.
- Regression cases keep every refusal condition fail-closed. Static result: 48 preflight-scan tests passed, project_status Structure/design PASS, Python compile, shell, JSON, and diff checks passed.
- Runtime: the same #316 profile ran as #317, reached z=0.5 m, and captured a fresh same-epoch `normalized_cost_exceeded` lockout during the second yaw segment. See the runtime report.
- N08 remains in progress; no goal/control enable is allowed without all same-run gates.
