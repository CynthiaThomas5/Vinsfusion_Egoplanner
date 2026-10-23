# 第1个小目标完成：测到原始VINS累积漂移

> **2026-10-22 坐标审计更正**：本报告下方原始位置／航向误差把 `base_link` 到 IMU 的安装偏移重复加到了 `d435i_link` 真值上；原数值已由同点坐标复算取代。正确重算：epoch `2a3d6786e1e544f886d3ec415549a70b`，2365 对、344.388 仿真秒，位置 RMSE 3.5481cm、最大 7.3980cm、末端 6.6236cm，yaw RMSE 0.4161°、最大 0.7331°；三次新增返回漂移为 1.855、3.732、5.716cm，新增 yaw 为 0.248、0.424、0.655°。它没有 raw VINS 速度及回调接收时刻，因此不计入 N01 的三个全状态 epoch。原始记录保留；完整更正和支持范围见 [N01 报告](vio-full-state-baseline-20261022-083.md)。

完成的是重复返回漂移测量，**不是“不漂移”验收通过**。同一epoch连续采集344.388仿真秒，参考停留至第3次返回相隔301.116秒，3次返回均满足预先固定的实际姿态重复性条件。VINS算法、健康阈值、控制链路和安装binary未改，没有启用回环后端或推进后续小目标。[机器报告与原始数据哈希](odometry-drift-20261022-069.json)。

| 停留点 | 相对参考累计实际IMU路程 | 固定初始对齐的位置误差 | 相对参考新增位置漂移 | 固定初始对齐的航向误差 | 相对参考新增航向漂移 |
|---|---:|---:|---:|---:|---:|
| 初次参考 | 0m | 0.66cm | 0 | 0.008° | 0 |
| 第1次返回 | 2.475m | 2.23cm | **1.85cm** | 0.256° | **0.248°** |
| 第2次返回 | 4.948m | 3.96cm | **3.73cm** | 0.432° | **0.424°** |
| 第3次返回 | 7.421m | 5.87cm | **5.72cm** | 0.663° | **0.655°** |

以上取各停留段最后5秒的源时间配对样本。位置“新增漂移”为平均估计误差向量相对首次参考的变化范数；航向为对应有符号误差的变化，不是用两个位置误差范数相减。每帧误差先扣除该帧实际真值运动，因此没有把支架约1.02cm的参考高度稳定差误算为里程计漂移。3次返回的实际yaw相对参考仅约−0.0008°；实际位置／yaw都在运行前声明的2cm／1°实验重复性容差内。容差不用于判断里程计精度或放宽健康门。

**在这条固定、缓慢、局部往返路线中，返回位置和航向误差逐次增加。** 四个停留点的描述性拟合约1.14cm/min、0.128°/min；单次实验不足以证明长期线性增长规律，但已经不能以“TRACKING正常”宣称没有漂移。

![实际路径、误差曲线和逐次返回漂移](../../artifacts/runs/odometry-drift-20261022-069-01/return-drift.png)

全过程2365对有效raw VINS／真值，位置RMSE3.61cm、最大7.40cm；yaw RMSE0.416°、最大0.733°，无真值插值拒绝。全观测区间配对真值IMU路程8.613m（含提升和下降）；每次单程平移仅1.2m，远端转出0.3rad再转回，不能外推长距离、多场景或实机性能。只在初始静止期间用一个位姿作SE3对齐、尺度固定1，不拟合整段轨迹，不对各次返回重新对齐。

运行`odometry-drift-20261022-069-01`，epoch `2a3d6786e1e544f886d3ec415549a70b`：342秒配置运动＋阶段/清理开销，工具墙钟433.034秒，23段全部完成，outcome为unarmed_support_drift_completed，error为空；689个VehicleStatus样本均DISARMED。支架脱离且移除收到确认，随后实际模型清单亦无支架。停止前再次读到arming_state=1，stop退出0。原有两个无关容器未动，Nano未改，未提交／推送。

验证：196项回归8.860秒＋真实ROS action／250Hz时钟集成通过，最大pose接收龄0.053秒。新增测试验证多次返回不会被重新对齐抹平、实际姿态不匹配不能通过、缺少返回不能完成，以及不接受非单调源时间。安装ROS／VINS代码未改，未重编；保护源码和本轮冻结输入哈希无差异，运行前后runtime fingerprint一致。结构检查仅验证骨架，不代替本轮实际未武装仿真或未来飞行。

主要命令：

```bash
bash tools/project.sh test
bash tools/project.sh sim odometry-drift-20261022-069-01
# 同一容器source ROS/install后，独立记录器先启动：
python3 tools/debug_truth/record_fixture_truth.py artifacts/runs/odometry-drift-20261022-069-01
python3 tools/probe_preflight_scan.py --run artifacts/runs/odometry-drift-20261022-069-01 --profile drift
python3 tools/debug_truth/evaluate_fixture_odometry.py artifacts/runs/odometry-drift-20261022-069-01
python3 tools/debug_truth/evaluate_return_drift.py artifacts/runs/odometry-drift-20261022-069-01
bash tools/project.sh stop odometry-drift-20261022-069-01
```

运动protocol在启动前保存于069-checks/planned-protocol.json，并复制到run/drift-protocol.json。checks还保存路线审查、文件快照、冻结哈希、测试日志和绘图脚本；run保存完整遥测、独立源戳真值、阶段、逐帧误差、return-drift.json和图。在线真值仅由debug_truth记录，未反馈定位或控制。此基线只测量漂移；下一小目标须由用户另行审阅后实施。
