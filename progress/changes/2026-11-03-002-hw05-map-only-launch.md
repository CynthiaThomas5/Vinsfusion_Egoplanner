# HW05 hardware map-only path — completed

Status: **passed for the bounded real tabletop scan and map lifecycle**. User authorized all HW05 exits in Goal completion mode. [Evidence](../evidence/hw05-depth-map-20261103.md), [dialogue](../../collaboration/dialogues/2026-11-03-002-hw05-ground-map.md).

## Actual changes

- Added `tools/hardware_mapping.launch.py`, `config/hardware/mapping.json` and `mapping_input.json`: direct existing EGO map-owner/adapter startup, system time, shared real rig, 0.10 m grid, explicit tabletop/local range, isolated goals and no trajectory server/control consumer. The deployed vendor launch is not used or modified.
- Mapping adapter accepts a selected project-local policy. Hardware CameraInfo must match the real rig; valid/TRACKING localization and map-reset acknowledgement are required. Invalid localization clears pending inputs/map identity. Hardware status waits for the first forwarded map input; actual fusion is independently confirmed by the snapshot service. RGB-disabled sessions produce no RGB-D keyframes. Simulation health semantics remain unchanged.
- The measured 0.3335 s optimized gap / 0.5444 s source age justified hardware-only bounded interpolation 0.35 s, pending wait 1 s and queue 16. The hardware map source timeout 0.868 s follows the retained 0.868306 s localization optimized-source budget. Original image source stamps and pose interpolation are preserved.
- Sensor conversion adds optional `max_output_rate_hz`; zero retains the original unrestricted behavior. The launch argument and hardware helper pass it through. The tested mapping profile caps only metric-depth conversion at 5 Hz; native camera settings stay unchanged. Values, zero-invalid semantics, source stamp and frame are preserved.
- Hardware localization reads stereo Image CDR metadata/sequence length without converting unused pixels. Added strict one-second continuously fresh startup admission; numerical source/receipt budgets stay configured. A stale newly paired solution cannot reopen INITIALIZING to bypass TRACKING freshness enforcement. Default simulation admission and typed-image input stay unchanged.
- Added a persistent read-only observer with exact-identity snapshot archives and reset-identity events, plus targeted ROS metadata/conversion checks. All attempts and refusals remain archived.

## Verification commands and results

- Nano: `colcon build --executor sequential --packages-select uav_sensor_interface uav_mapping --cmake-args -DBUILD_TESTING=OFF`: **2 packages passed**; log in run06.
- Nano: `colcon build --executor sequential --packages-select uav_localization --cmake-args -DBUILD_TESTING=OFF`: **passed**, including final run09 build.
- Nano: `python3 tools/test_depth_output_rate.py`: **passed**. Unrestricted output 60/60; capped output 15/60; units/zero/frame/source stamps preserved.
- Nano: `python3 tools/test_image_metadata.py`: **2 tests passed**, installed ROS serializer and malformed/truncated input.
- Workstation: `python3 tools/test_localization_health.py`: **13 passed**; `python3 tools/test_mapping_input.py`: **6 passed**.
- Python compile, `bash -n tools/hardware.sh`, `python3 tools/project_status.py`, `git diff --check`: passed. Structure checks do not substitute for hardware runtime.
- `python3 artifacts/runs/hw05-analysis-20261103/analyze.py`: snapshot hash/array/count/class/identity/source-age/reset/shutdown assertions passed.

## Runtime result

Final same-map scan through operator completion: **143 s**, no invalid localization samples, maximum pending queue **3**, no additional drops; optimized/propagated output **6.12/146.9 Hz**, depth forwarding **4.21 Hz**. The operator's 25–26 cm vertical target agrees with central occupied-cell medians **23.8/23.7 cm** before/after motion at 10 cm voxel resolution. ROI Jaccard **0.90**; the pre-existing adjacent depth span did not grow. These are coarse occupied-cell observations, not sub-voxel surface accuracy or full-scene ghosting qualification.

Same map owner PID158581 retained across epoch09→epoch10. New identity had zero pending/occupied/previous source stamp with reset acknowledged. Old epoch query was rejected and a new 36-occupied-voxel snapshot was read back. VINS stop invalidation and normal owned shutdown were verified; final ROS node/project-process lists are empty. Temporary rmem restored to saved **212992**.

## Limitations and next item

Earlier startup and longer concurrent-load lockouts remain real and are listed in the evidence. The one-thread VINS trial did not solve them; final runs used four threads. Average CPU benefit of metadata-only reads was not demonstrated. HW09 must qualify complete load/headroom. Calibration/airframe installation remain PROVISIONAL/unmeasured.

The pre-existing deployed vendor source/launch differs from the canonical source lock, and clean replay failed at Foxy patch0062. This module records exact final deployed source/binary identities and leaves vendor sources/patches unchanged. Canonical reconstruction and planning-source audit remain required before extending planner qualification. Historical pre-window policy values are normalized in artifacts; no byte-identical old-policy recovery is claimed. Final epochs09/10 have exact current configuration fingerprints.

Stop reason: **all authorized HW05 exits completed within the bounded ground test**. Next: **HW06.1 source audit and compute-only interface work**, not started. No SITL, PX4, navigation goal or flight was run.


## Final deployment audit correction

A successful incremental build did not establish installed-code equality. The final audit found old installed `node.py` and `health.py`: the source timestamp was on Nano date2026-10-19, while the installed node file was dated2026-11-02. Thus runs01–10 did not exercise the new CDR callback or stable-window gate. Their actual geometry/map data remain retained, and their code coverage is explicitly limited.

Backed up the old generated install prefix and default build cache under `artifacts/runs/hw05-clean-localization-20261103/`; marked the backup root COLCON_IGNORE after an initial duplicate-package discovery refusal. Built the localization package with a fresh build directory, refreshed the default package build cache, and compared actual imported modules with source. Added startup refusal on localization module/source mismatch to `tools/hardware-localization.sh`.

Final installed/source equality passed for six actual localization/mapping/rig modules. Imported Health reported startup_fresh_window_s=1.0. With actual current code, epoch11 and epoch12 stayed valid133/168s, each with the stable-freshness admission reason observed and max pending queue3. Same final map owner PID195432 retained across the restart; empty reset, old-epoch rejection and a fresh38-occupied-voxel map passed. Current-code central cell medians were23.2–23.7cm, consistent at0.10m resolution with the same25–26cm target. The changed metadata/admission path was checked on real images and completed-map readback; unchanged movement geometry was reused, without a third operator motion.

Latest run12 node/process lists are empty and rmem restored to212992. Both the old installed modules and final actual-module fingerprints are archived. Average CPU gain remains unproven. Final status is passed only after this corrected deployment audit and affected runtime validation; HW06 remains not_started.
