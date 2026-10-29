# #280 Runtime manifest launcher fingerprint fix

`runtime_manifest.py` now includes the installed `navigation_supervisor` launcher in its runtime file snapshot. A focused temporary-tree regression test verifies this executable is retained in the manifest. The live workspace snapshot now records SHA256 `c9ddb17931ef244d150caffe9f04164c3fd2ba76160cd02b03c7455267c11923`, matching the #276 N08 build record.

Verification: the targeted unittest passed (1/1), `bash -n tools/sim_runtime.sh tools/mission_runtime.sh` passed, and `git diff --check` passed. This closes a pre-control fingerprint bookkeeping defect only; N08 flight qualification remains pending.
