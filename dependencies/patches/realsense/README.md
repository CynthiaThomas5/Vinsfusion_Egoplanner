# RealSense hardware SDK patch chain

Base: librealsense bf2778061d5dd29776e9aca8765f75852671760b (2.58.1), Apache-2.0.
Read-only source: /home/jetson/realsense_debug/librealsense-v2.58.1.

Order:
1. 0001-hid-hold-sensitivity.patch: existing measured HID interface hold/sensitivity fix, original /home/jetson/realsense_debug/hid-hold-sensitivity-sdk2581/hid-hold.patch, SHA256 57e25c0f8ddfce20ac82d86dde4ac445af5f50a6a27bc71b8e9e0f30887cc457. Existing runtime library a72cc3c5030be54ee532347d10a40b3839535bc79b2b4709d10d452c370b69f9.
2. 0002-robust-global-clock-fit.patch: clock translation unit only; no class layout/API changes. Backports robust Theil-Sen clock fit and blend clamping from upstream 6ffa0618b039b95e5c272720a21ff7373c13d57e (src/global_timestamp_reader.cpp); skips slow (>10ms half-RTT) warmup reads before any accepted sample, adapting upstream's slow first-read rejection without adding ABI state. Does not clamp timestamps to now, change health budgets or global-time settings. Current candidate qualification is recorded in progress/evidence; not flight-qualified merely by applying this patch.

Upstream: https://github.com/realsenseai/librealsense/blob/6ffa0618b039b95e5c272720a21ff7373c13d57e/src/global_timestamp_reader.cpp

Copyright RealSense, Inc.; source Apache-2.0 notices preserved. Only the isolated build is modified. tools/build_hardware_sdk_clock.py first relinks every original HID build object and requires exact original library SHA, then replaces only clock.o and writes all link input hashes. It reuses verified objects in the read-only existing build; neither source nor original install is edited. A clean SDK build can apply patches in order normally. Do not mix arbitrary versions/objects.
