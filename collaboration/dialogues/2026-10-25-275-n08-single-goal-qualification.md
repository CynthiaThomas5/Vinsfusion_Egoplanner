# #275 子项对话摘要：单目标验收与候选降落证书

- 用户授权按N08完整规划持续完成N08；继续单D435i仿真，不做实机或任意返航测试。已通过N07不复测。
- 当前首项：实现普通单目标评估，不要求转向／home action；检查新终点的fresh raw-map下降和允许触地体积。普通目标抵达／保持后若要落地，降落是单独收尾命令，须使用候选地面几何，不能伪造实际landed状态。
- 保留#260/#267/#273所有去程制动记录和原往返整轮FAIL；离线存档可以排查几何，不当作当前版本资格。容器无活动的项目仿真，停止状态已确认。
- 源码路径已确认：navigation caller cancel→MODE_ABORT→traj_server ABORT→bridge trajectory_fault→LANDING；后续实现须区分正常取消与故障中止，并在地图／停止边界有效前不执行取消飞行。
- 当前数值语义冲突待审计：0.12m/s配置声明为实际向量界，但已有watchdog／离线检查是0.15m/s水平界；线上估计跟踪0.15m与raw-map 0.25m空间余量分别保留。
- 本子项允许修改runner、evaluator、候选着陆几何／N05适配和定向测试；不改未知、健康、速度门限或5cm管道。

## 2026-10-26 实施进展

- 用户将范围明确为“按规划完成N08”；已进入Goal完成模式，继续当前N08而不推进N09或实机。
- 普通goal采用`single_goal`流程；`round_trip`保留显式兼容，只有选中时才走转向／home动作。目标区落地先从home raw plane投影实际机体standoff，再用同run新地图重验hold、下降、contact候选；报告始终标记`ground_confirmed=false`，只有bridge/PX4实际反馈确认落地。
- #260 airborne map、#267 airborne map、#273 post-goal/pre-turn map的候选下降回放3/3支持`candidate_landing_volume_known_and_clear`，unknown/occupied均为0。这只是历史geometry replay。报告见`progress/evidence/n08-candidate-landing-archive-audit-20261026-277.*`。
- 普通caller cancel当前错误地按abort导致traj_server发ABORT并由bridge进入LANDING。#0046新增`MODE_STOP_HOLD`：EGO基于当前运动速度向前生成替换停止曲线；保留现有整曲线及terminal-hold raw-map证书，规划／状态／速度不满足或证书失败继续ABORT安全落地。停车点系历史最大末端停车距离0.30234m按当前速度缩放，再加0.10m候选余量，限于当前低速前向实验，不宣称一般制动保证。第三方补丁基准commit与补丁SHA写在`dependencies/patches/ego/README.md`及`sources.json`。
- 首轮ROS build通过，333项全套回归通过，候选映射／制动／候选落地定向用例39项通过。此次构建包含#0046；运行前仍须确认新build evidence和mission source/binary fingerprints完全匹配。
- 尚未跑任何#0046 caller-cancel SITL，也未开始最终同版3次普通单目标重复；父N08不通过。下一步先完整取消停车低速SITL并测实际路径／hold／落地；必要时修正后重建回归，再跑受控对照、预算接入、版本冻结和3次独立普通单目标。
