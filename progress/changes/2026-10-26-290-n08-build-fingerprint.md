# #290：更新 N08 caller-cancel build fingerprint

## 目标

让当前EGO patch 0047构建通过N08 runner的严格来源与二进制身份门；保留运行前拒绝行为。

## 证据与修改

#290同一冷启动中N05 6/6、夹具移除、post-release和mission current-area online/offline准入、40.001s只读preflight全部通过。随后runner在goal/enable前报`trial_source_fingerprint_mismatch:dependencies/sources.json`：它引用#276（0046）构建记录；当前sources锁已包含0047。

- 新增[#289 build evidence](../evidence/n08-cancel-stop-build-20261026-289.json)，锁定0047 patch/source、installed EGO/接口/导航二进制、runtime scripts、17包colcon build和348项回归。依赖的完整patch replay通过。
- `tools/run_n08_braking_trial.py`改为使用该当前build evidence；Python runner/helper依旧在每次run的runtime manifest逐字节校验。
- PX4/bridge readback表明本次从未enable：bridge DISABLED、PX4 disarmed/landed、三类控制消息0。随后项目容器安全停止。

## 验证与限制

- `bash tools/project.sh build ros`：17包通过；日志在`artifacts/runs/n08-cancel-stop-build-20261026-289/build.log`。
- `bash tools/project.sh test`：348项单测和navigation-adapter integration通过；路径更新后已再跑一遍，日志在同目录`test.log`。
- `python3 tools/fetch_dependencies.py --source ego_planner --target /tmp/n08-ego-patch-replay-289`：固定上游和0047完整patch chain回放/hash通过。
- #290拒绝发生在N08 goal之前；没有取消、替换轨迹、制动或SITL执行证据。

下一步#291用新冷启动复跑N05→preflight→current-area admission→motion-cancel，确认0047 runner build身份门通过。
