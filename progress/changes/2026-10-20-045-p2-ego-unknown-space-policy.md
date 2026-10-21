# GOAL C EGO unknown-space collision policy experiment #289

对应对话摘要：[2026-10-20-045](../../collaboration/dialogues/2026-10-20-045-p2-ego-unknown-space-policy.md)。轻量证据：[p2-ego-unknown-space-policy-20261020-289.json](../evidence/p2-ego-unknown-space-policy-20261020-289.json)。源码副本、候选patch、fresh build、planner-only运行与哈希见 `artifacts/runs/p2-ego-unknown-as-obstacle-experiment-20261020-289/`。

## 结果

- 静态代码审查确认：EGO `GridMap::isUnknown` 可识别未观测体素；基线 `getInflateOccupancy` 只返回膨胀占据位，unknown体素的位为0。B-spline碰撞检查和A*把非零值当作障碍，因此基线实际把unknown当作free。
- 新增候选patch `dependencies/patches/ego/0020-unknown-as-obstacle-experiment.patch`，仅在run-local EGO源码副本应用；输入为固定EGO commit和canonical 0001–0011、0017–0019。`patch --dry-run`通过，`traj_utils`、`plan_env`、`path_searching`、`bspline_opt`、`ego_planner` fresh build 5/5通过。`src/vendor/ego_planner`未修改，候选patch未加入`sources.json`标准链。
- #289在ready地图902点、15,360膨胀点下派发目标，捕获91条B-spline。首条离线单SE(3)位置RMSE 7.53 mm、P95 13.49 mm；相对名义0.482 m球半径的箱体／圆柱计算余量0.222/0.346 m。离线已知碰撞体结果不代表unknown空间或实际跟踪安全。
- 同轮EGO有82条`odom or depth lost`、81条`Depth Lost! EMERGENCY_STOP`、2,747条终点落入障碍告警和22条“suddenly discovered obstacles”消息。前两段EGO同步计数分别卡在439和538；对应MapStatus仍ready、转发depth计数466→482及583→597，独立优化里程计订阅也继续收到样本。末段同步计数增至796，但`last_sync_in_map=false`，呈现另一类局部地图范围拒收。mapping gate因normalized cost关闭前，第一、二段超时分别约早19.34秒和12.74秒；最后一段与关闭时刻相邻。读端DDS／执行器与局部地图范围仍需区分。
- 无控制节点、控制话题、PX4、真值订阅、轨迹服务器或控制器；规划器内部FSM与B-spline没有执行。GOAL C/D/E/F不通过。

## 修改与验证

- 新增候选第三方patch及`dependencies/patches/ego/README.md`来源、应用顺序和局限说明；未修改固定vendor源码、PX4或自维护控制代码。候选patch只进入run-local源码副本。
- #289 `patch --dry-run`通过；fresh Jazzy EGO 5包build通过；运行捕获B-spline；离线固定尺度SE(3)评估完成；运行报告原始文件SHA-256逐项核验。
- `python3 tools/project_status.py`：PASS（Structure/design check）；`git diff --check`、`git diff --cached --check`：PASS；#284–#289运行报告原始文件哈希逐项复核，#285五项归档产物哈希也复核通过。

## 状态与下一步

unknown-as-obstacle是符合GOAL C安全方向的候选，但#289输入超时和规划拒绝过多，尚不能进入canonical依赖链或用于正式导航。继续对齐EGO reader/message-filter/executor与局部地图边界；补occupied/free/unknown计数、覆盖、快照几何和持续性验证。保持GOAL C/D/E/F pending及P2阈值PROVISIONAL。
