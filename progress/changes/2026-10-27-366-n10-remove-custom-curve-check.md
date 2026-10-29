# N10.3/#366：移除项目自加的全曲线准入并恢复上游重试

## 背景与判断

#365 的障碍创建和相机/地图观测均发生；后续EGO样条几何开始绕开箱体，但 native `reboundReplan` 在后续一次优化中报告 refined trajectory collision、返回 `planning_failed`。源码审计发现补丁0039将上游 `SEQUENTIAL_START`／`GEN_NEW_TRAJ`／`REPLAN_TRAJ` 对不可行规划的状态重试替换成 `stopForSafety("planning_failed")`，导致目标立即中止。此外，项目自加的 `certifyLocalCurve` 调用仍围绕新曲线／活跃曲线／停止曲线执行地图就绪与整曲线检查；0049虽在 `official_ego` 下旁路raw occupancy sweep，仍会先执行 query readiness。

用户明确授权删除阻断任务的本项目附加保护。N10 当前已要求官方 EGO inflated-occupied 碰撞语义。因此本项仅删除额外 `certifyLocalCurve` 活动调用，并恢复上游重试；不更改 EGO 自身优化／inflated-occupied碰撞、原生未来轨迹碰撞回调、深度超时、emergency-stop、PX4 bridge 控制所有权。

## 修改

- 新增第三方补丁 `dependencies/patches/ego/0053-remove-custom-full-curve-gates.patch`，并将其登记到 `dependencies/sources.json`；固定上游基准与补丁顺序不变。
- 删除EGO FSM四处自加整曲线/地图就绪证书调用及私有helper；保留地图诊断API供离线/只读路径使用。
- 将三处 planning_failed 立即中止恢复为上游状态重试。
- patch SHA-256：`529fcade428165d4101cdc660b38f1cfd0094f22f0f77d03530e5808de7bb727`。

## 验证

- `patch --dry-run --batch -p1 -d src/vendor/ego_planner < ...0053...patch`：修改前预检查成功；已应用后再次 dry-run 识别为反向/已应用。
- `bash tools/project.sh build ros`：17/17 ROS 包成功；日志[`build.log`](../../artifacts/runs/n10-20261027-366-ego-patch-build/build.log)，SHA-256 `ad6631f7a7725e4a78d0f2eed195f08ea4ca6be78f656bfb8ebe4037fb575b0a`。
- EGO 节点SHA-256：`25179a8ccdec7489c463f02e662180327bd34f90ef293ab1d0a0a85593d4982b`。
- `bash -n` run-local driver、`python3 -m py_compile` run-local injector/analyzers、`git diff --check`：通过。
- 构建后 runtime contract SHA-256：`15d935eb803e76eb378aa4aa566d2d7b46b97168e2c75e7e0ee5d87878ed57a6`（665项）；本轮只用于诊断候选，不是最终冻结。

## 限制与下一步

#365 不能证明是立即中止以外的自定义曲线证书导致规划器不可行；日志表明EGO原生优化确实未找到曲线。#0053用于让上游重试行为继续运行，等待同场景SITL复测。当前 N10.3/#367 已冻结新runtime、协议与观察器，尚未启动。完成后继续定量支持范围和唯一验收配置。
