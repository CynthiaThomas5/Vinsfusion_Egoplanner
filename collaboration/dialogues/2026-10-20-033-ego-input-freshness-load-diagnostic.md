# GOAL B/C EGO 全栈输入新鲜度与短目标诊断 #259

## 任务摘要

在不改健康策略和项目配置的前提下，保留0.5 m运行期膨胀、mapper、EGO与健康门，直接观察双目和IMU输入源龄；只有定位、地图和占据满足稳定前置条件时才发一个0.7 m短目标。运行不接控制器、PX4、setpoint或在线真值。

## 已确认

- 左／右图各收到1,152帧，3 ms内配对1,151组；接收时源龄最大110/129 ms。IMU收到7,066条，源龄最大31 ms。未见观测源龄或仿真接收龄越过现行健康阈值。
- 定位进入TRACKING后，在55.066秒直接输入观察窗内未出现`left_stale`或`imu_stale`。
- 健康和地图门满足后，目标(0.7, 0.0) m被发送；map有915个占据点，收到一条相同epoch的三阶B-spline。没有轨迹服务器或控制器，因此轨迹未执行。
- EGO日志仍记录98条`odom or depth lost!`，分三簇8/10/80条；采样日志中的最后同步位姿均在图内。观察到一次`refine_success=1`和一次进入`EXEC_TRAJ`状态日志，没有终点障碍警告或`EMERGENCY_STOP`。
- raw VINS有680条优化、8,981条传播和690条telemetry；输出有限，无解析错误或真值样本。run-local wrench激励仅由`/clock`驱动。

## 决定与限制

- 将结果记为规划输出诊断，不把B-spline发布视为轨迹跟踪、避障或净空通过。
- 独立传感器观察器不能证明每个样本都由定位／建图适配器收到；观察器也给DDS与回调增加了额外负载。
- 上游源龄和定位健康未越限，但EGO更新超时仍发生。mapper到EGO交付／同步边界是下一步检查方向，不是已证明根因。
- 0.5 m膨胀和−0.05 m地面界限仍为run-local诊断值；GOAL状态和P2健康阈值不改变。

## 待决问题

- 三簇超时内，mapping adapter发布、EGO reader take和同步回调各自的源戳／接收戳是否连续？
- 日志中的EGO超时与adapter到EGO的实际消息交付间隔是否对应？

详细数据和哈希见[证据报告](../../progress/evidence/p2-ego-input-freshness-load-diagnostic-20261020-259.json)；原始日志及样本位于`artifacts/runs/p2-ego-input-freshness-load-diagnostic-20261020-259`。
