# #413 N10 offline source and archive audit

Completed a read-only, same-epoch replay of #404/#411/#412 VIO/yaw/RPE, host replay of model-bounded interval clearance, source-lock comparison, raw-free voxel/raycast source review, and #412 resource/VINS-queue summary. Added a reproducible audit script and lightweight Markdown/JSON evidence.

Corrected #412's free-voxel face attribution: 35 of 39 cells are nearest the positive-Y face and 4 the negative-X face; no ROI cloud watermark was observed. The 39 cells remain unattributed and raw-map classification remains `FAIL`. The host replay shows that #404/#411 do not bind the current source-lock SHA, so their computed interval minima remain identity-insufficient; #412 passes the complete identity chain and is the only newly qualified interval replay. Within-run yaw/RPE grouping supports a targeted rate experiment, but does not establish causality. #412's representative resource sample cannot define VINS capacity or a ten-minute growth limit.

No flight, runtime behavior, parameter, or acceptance threshold changed. Validation: audit script reran successfully; report and all generated run JSON parsed; `git diff --check` and repository structure check are recorded after the documentation update. N10 remains `in_progress`; next subtask #414 is a fixed-route, single-variable yaw-rate-cap calibration with read-only map-source evidence.

Evidence: [#413 report](../evidence/n10-offline-source-audit-20261028-413.md), [machine-readable report](../evidence/n10-offline-source-audit-20261028-413.json), [dialogue summary](../../collaboration/dialogues/2026-10-28-413-n10-offline-source-audit.md).


Follow-up source correction: inspected the #412 run-local injector and recorded its every-tenth-cloud sampling, injection −0.5 s to +5 s ROI window, and +8 s fallback snapshot. Updated the #413/#412 reports so the prior `no_roi_cloud_observed` label is explicitly coverage-limited and cannot support an absence claim. #414 will correct observer coverage and record per-voxel update contributions.
