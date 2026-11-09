# Hardware-only bounded stage timing

Upstream lineage: zinuok/VINS-Fusion-ROS2 at `72023bc5d2abb14faa4c02a5c040d84f996b587a`, GPL-3.0. This patch applies to the **current Nano hardware source**, estimator.cpp SHA256 `42caabee7725cf7a771f7cc50b811f6244f221a7709573e15d55ad391b865a02`. It is not automatically applicable after the frozen simulation patch sequence; that default list and dependencies/sources.json remain unchanged.

Apply `hardware-stage-timing.patch` only to an isolated source copy with that exact hash. It records tracking, process-lock wait, processImage, marginalization and publication (including the existing statistics/header preparation) using steady_clock. `VINS_STAGE_TIMING=1` enables stderr records with phase, original source time, elapsed milliseconds, and monotonic end seconds. processImage contains solver/marginalization: do not add nested timings. Calls add clock-read overhead even when logging is disabled; the candidate is diagnostic only and is restored after the bounded experiment.

The run-local builder uses the actual recorded compile command, adds only the original source include directory for the relocated copy, replaces one estimator.cpp.o in a private archive and relinks with the original link command. It never changes vendor source or original build objects. Installed binary replacement is temporary, only after confirming no perception session; original SHA is restored after owned shutdown. Do not install this candidate as a qualified flight binary.

Build scripts, exact command arrays, source/binary/archive hashes, baseline and candidate and runtime evidence live in artifacts/runs/hw10-stage-20261105-011. The progress evidence records build/runtime limitations. Timing is diagnostic data, never a source-health substitute, and does not change equations, queue policy, thresholds or control.

HW10-STAGE-011 built and ran the five-phase candidate; baseline relink reproduced the existing build target byte-for-byte. Final performance change uses the original installed binary with hardware OpenCV threads=2. The timing candidate is not installed after the test. See progress/evidence/hw10-stage-20261105-011.md.
