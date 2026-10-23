# #074 回环候选拒绝阶段诊断

## 结论

完整fresh epoch中，50个已检索候选均产生逐阶段诊断：45个因PnP/RANSAC内点数不超过25而拒绝，1个通过内点数筛选但因yaw超出现有30°限制而拒绝，4个通过原验证条件。BRIEF描述子匹配数为57–109，因此这次没有候选停在描述子匹配数量门。没有修改候选逻辑、PnP/RANSAC、判定阈值或定位健康门。

这说明了这条固定支架路线上的主要拒绝阶段，不表示里程计漂移已降低或消除。

## 实施与静态验证

补丁`dependencies/patches/vins/0019-loop-candidate-diagnostics.patch`基于固定VINS上游提交`72023bc5d2abb14faa4c02a5c040d84f996b587a`及0018。它观察每个候选的BRIEF匹配数、PnP输入数、`solvePnPRansac`布尔返回值、RANSAC内点数、相对偏航／平移和既有门限结果，再通过已有只读status按批输出。注释掉的Fundamental RANSAC保持关闭；诊断缓冲每批最多512条，并显式统计溢出。

- 固定上游全量fetch重建成功，全部已登记vendor文件哈希匹配。
- `bash tools/project.sh build ros`成功：17个ROS包完成，loop_fusion重编。
- `bash tools/project.sh test`成功：199项单测及导航ROS action集成通过。最终检查`git diff --check`通过。

## 运行结果

首轮`real-loop-20261022-074-01`使用fresh epoch，但在路线第29/47段触发原定位健康门，q=1.1243，探针以FAIL结束。它留下9个候选事件，不并入完整路线统计。所有VehicleStatus样本仍为DISARMED；之后用已有attached记录和Gazebo模型清单确认支架，安全复位并收到detached／移除确认。该次失败、清理记录和原日志均保留。

第二轮`real-loop-20261022-074-02`使用fresh epoch `d612f794c58d4c898a03adcc1d7603b0`，完成47/47阶段，耗时842.72墙钟秒。探针观察到1486个VehicleStatus样本且均为DISARMED，定位结束时仍有效，支架已detached并移除。最终状态为101关键帧、50候选、4条验证边、4次优化；后端正常退出码0。

| 候选验证阶段 | 数量 | 观测 |
|---|---:|---|
| PnP/RANSAC内点`<=25` | 45 | 14次函数返回false且均0内点；另31次返回true但内点仍不超过25 |
| 相对yaw门拒绝 | 1 | KF67→KF7，29内点，yaw 67.7775°失败，平移4.9581m通过 |
| 完全接受 | 4 | KF63→5、KF68→7、KF92→4、KF94→6 |

50个事件序号从1连续到50，候选诊断丢失0条；事件数等于`loop_candidates`，接受事件数等于`verified_loops`。四条实际回环约束通过独立debug_truth几何复核，平移误差1.82–3.50cm、姿态误差0.109–0.317°。13项回环观察核验全部通过：没有真值订阅、控制或TF输出，输入与时间配对、缓冲上界均符合要求。完整事件和矩阵见运行目录中的`candidate-diagnostics-summary.json`、`loop-observation.json`及`real-loop-evaluation.json`。

## 限制与下一小目标

这是一条理想仿真房间中的未武装支架路线；首轮因既有健康门中止，已明确保留。当前证据没有回答四条回环是否降低raw VINS的全程漂移。下一建议目标是固定初始静止位姿对齐、尺度1、闭环后不重对齐，仅对074-02的raw轨迹、回环修正轨迹与独立真值做离线误差对比；尚待用户批准。

机器报告：[loop-candidate-diagnostics-20261022-074.json](loop-candidate-diagnostics-20261022-074.json)。
