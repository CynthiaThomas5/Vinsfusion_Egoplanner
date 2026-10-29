# N08 #323：早期 VINS telemetry freshness 锁存，未进入支架扫描

## 结论

新 PX4/VINS 会话在初始 N05 raw-map 检查时，150 秒内没有收到 /localization/optimized_imu_odom，因此按原门限拒绝；mission、支架扫描、goal、bridge enable 和 flight 均未启动。该 run 不计入三次普通 terminal_stop。

这次冷启动的直接锁存原因可从 localization adapter 原始日志复算：在仿真 t=9.78 s，telemetry 样本源龄为 0.340 s，超过现有 0.300 s source-age 门限 0.040 s。receipt age 为 0.308 s，仍低于 0.500 s 限值；normalized cost 仅 0.08980。状态随即变为 LOST/telemetry_stale 并锁存。该次锁存不是 EGO、N05 空间几何、PX4 disarm 或 normalized-cost 拒绝。

## 证据链

- 首个 N05 checker 记录：收到 localization、map、bridge、clock，缺 optimized odom；超时 150 s，online truth/control/goal 均未使用。
- health_lockout_snapshot 位于 artifacts/runs/n08-terminal-stop-20261026-323/vio.log：clock=9.780 s，last pair=9.440 s；telemetry source stamp=9.440 s、receipt clock=9.472 s；source age=340 ms，receipt age=308 ms；原门限分别为300 ms和500 ms。
- 此时 solver_usable、solve_current 和 state_finite 均 true，normalized cost 0.08980/1.0。锁存后 VINS 原始 odometry、IMU propagate 与 telemetry topic 继续发数据，但 localization adapter 不恢复有效 optimized odom；后续 status 仍是 LOST、reason=telemetry_stale，source_stamp停在约9.536 s。采样频率和topic发现诊断保存在同目录 startup-*.log。
- 独立读回确认 bridge DISABLED、control disabled、PX4 arming_state=1、landed=true；控制模式／轨迹设定点／vehicle command 均0。fixture从未spawn。用户要求的安全清理已完成，容器退出0。

## 处置与下一步

freshness 限值保持不变。本轮不在锁存的同一 epoch 上尝试导航。由于这次具体失败是初始化阶段单个 340 ms telemetry 源龄窗口，且冻结版 #321/#322 已产生成功运行，下一项使用相同源码、构建、配置和镜像做新的独立 PX4/VINS/map 冷启动，检查该早期窗口是否复现。只有 fresh N05、支架释放、任务内准入、preflight、几何及 native/evaluator/安全收尾全部通过，才累计为普通目标成功。

runtime-contract SHA256 为 75aaa541f7684b38fe0805b958e029fa21f8c6dd6ab00d2ebe1fae92c7e8a772。全部数值、状态和原始文件哈希见同目录 JSON。
