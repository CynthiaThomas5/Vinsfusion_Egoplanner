# N10.3/#458 综合正常导航校准

用户要求继续完成 N10，保留 N10 Goal 完成范围；用户明确排除故障后校准，不做故障注入。上一轮 #457 的 `max_cnt=220` strict native replay 通过原有 VIO 数值草案，本轮据此安排一次正常 16 m 路线、动态障碍重规划和 20 sim s hold 的综合校准，采集资源、VIO、地图、物理步净空和跟踪证据。

验收阈值不变，所有统计离线使用，观察器缺失只报告不足，不影响起飞/控制/降落。只有独立末态确认 landed/disarmed/control-disabled/zero-control 才停止仿真容器。
