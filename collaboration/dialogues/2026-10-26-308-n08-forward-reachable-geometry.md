# N08 #308 对话摘要

## 用户目标与约束

- 用户授权按此前测试规划持续完成 N08。
- 普通目标到达后停止；不隐含返航。需要返航时，先结束当前 EGO 目标，再单独原地转180°，以第二个 EGO 前向目标返航。
- 不复测已通过的 N07；不放宽 unknown／occupied、速度、定位、tracking、地图新鲜度或连续性门限；静态检查不能算 flight pass。

## 本子项决定

- #305 后向 unknown 的球形拒绝先在归档地图离线重算；实现使用锁定 X500/D435i 碰撞件及同一空间和 tracking 预算，保持连续扫掠与完整起／终保持。
- 航向变化也进入机体外形扫掠。既有 N08 #294 PX4 local heading 相对目标的样本最大差0.015545rad；据此采用±0.019rad候选 geometry/watchdog范围，并保留后续新版本验证。它用于该固定航向试验，不改变 goal 的0.35rad容差。
- 单目标 runner 的 metadata 改为目的地点落地，无 return goal；只有单独选择 round_trip 才执行第二段转向和返航。

## 结果与待办

- #305 raw map 离线复算的0.6m普通目标和0.5m取消走廊、起点／终点保持全部通过，查询没有 unknown／occupied。
- 28项 N08 几何回归、374项全仓单测和 navigation adapter integration 通过。
- 未起飞、未发送目标；下一步 #309 必须获取 fresh same-run N05 与 N08实时准入，之后再按规划运行单目标和取消测试。
