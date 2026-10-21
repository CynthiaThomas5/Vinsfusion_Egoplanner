# GOAL C EGO pose reader 回执与同戳样条快照诊断 #345

用户要求继续完成 `GOAL.md`。保留工作区已有改动，只推进单 D435i 仿真导航；unknown仍fail-closed，唯一PX4控制发布者仍为`uav_px4_bridge`。本轮新增一个EGO run-local诊断补丁，未改canonical/vendor源码，没有真值、PX4、controller、trajectory server或控制话题。

决定：#0015的旧组合补丁上下文不能直接套到#341的实验源码树；新建0034，仅观测现有 `message_filters` reader回执、源戳和RMW丢失计数，不改QoS、ApproximateTime同步或0.4秒freshness门。补丁基于固定上游提交`23a8d5a191711dd65633df689bd00f55d4dea8f9`的#341源码副本，顺序为15个canonical补丁、实验0029/0030/0031/0028/0032/0033、再0034；隔离五包Release构建通过。

结果：#345新domain收到一条真实3D `NavigationCommand` 样条，pitch前后快照将目标体素从unknown变为known-free。EGO于18.658–19.552仿真秒发出27条timeout警告；depth reader计数390→417，pose reader和同步计数固定379、pose末戳18.184秒，两路RMW lost均为0。该间隔早于pitch/goal；没有同窗adapter侧位姿发布观测，发送端/DDS/executor原因未定。之后planner样条获得与start_time完全同戳的只读快照，源龄104 ms。独立de Boor完整活动区间103点中42点仍在当前起点unknown voxel、61点known-free，其余堵塞分类为零；曲线依赖run-local补丁0033起点例外，未执行且无机体扫掠证据。

结论：reader回执计数确认间歇性位姿输入缺口，但根因仍未闭合；准确同戳快照让该轮中心线占据分类更可靠，仍不满足GOAL C。下一步同窗对照adapter侧camera-pose输出和EGO reader回执，不调整QoS或timeout。未知策略和PX4边界保持不变。
