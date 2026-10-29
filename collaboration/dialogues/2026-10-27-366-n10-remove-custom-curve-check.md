# N10.3/#366 对话摘要

## 任务

用户要求继续完成N10，并明确项目自加保护措施若阻断任务应先核对源码并删除。沿#365动态障碍诊断追查EGO失败原因。

## 已确认

- #365的Gazebo方箱创建ACK成功，传感器/占据表面点云出现；目标最终因`planner_full_curve_planning_failed`失败并安全落地。
- EGO原生`reboundReplan`出现优化碰撞、`refine_success=0`；补丁0039新增的立即`stopForSafety("planning_failed")`将本应进入上游重试状态变成中止。
- `certifyLocalCurve`是本项目补丁引入的额外完整样条/地图就绪路径；官方策略虽绕过raw occupancy sweep，仍会经过本项目readiness调用。

## 决定与实施

新增补丁0053，删除自加的完整曲线准入调用、恢复上游规划失败重试；保留官方EGO inflated-occupied避障与原生碰撞检测、depth timeout/emergency stop、身份完整性和PX4 bridge控制所有权。无健康数值门限回加。

构建17 ROS包成功。新 runtime hash=`15d935eb803e76eb378aa4aa566d2d7b46b97168e2c75e7e0ee5d87878ed57a6`。#367协议、工具哈希已冻结，下一步是在相同目标与障碍场景中复测是否可由重试恢复。

## 证据

- #365结果：[progress/evidence/n10-live-obstacle-replan-20261027-365.md](../../progress/evidence/n10-live-obstacle-replan-20261027-365.md)
- #366变更：[progress/changes/2026-10-27-366-n10-remove-custom-curve-check.md](../../progress/changes/2026-10-27-366-n10-remove-custom-curve-check.md)
- #367协议：[progress/evidence/n10-live-obstacle-replan-retry-protocol-20261027-367.md](../../progress/evidence/n10-live-obstacle-replan-retry-protocol-20261027-367.md)
