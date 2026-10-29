# #378 SITL prelaunch freeze

状态：**容器启动前已冻结**。基于 #377 同 runtime 的 PX4 水平峰值 `0.647896 m/s`，仅把取消触发窗定为 `[0.60,0.66] m/s`；同目标／epoch READY 与有效 PX4 位置样本有 110 个候选。

- Runtime source/install SHA `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7`（候选 665 文件）；planner `config/components/mapping/n10_horizon5_speed080_calibration.json` SHA `0f92519ded6f367387998f01e19a27e270b94c7571e12fbe5b80f82b8ed7473e`；spawn `config/components/simulation/n10_long_range_spawn_minus8.json` SHA `b2534428e59c4b953e49f08a759b5cda8f1f0ea40f3a7d764923a797ff6f4aa2`，pose `[-8,0,0.3,0,0,0]`。
- Goal `config/components/navigation/n10_long_range_vio_calibration_goal.json` SHA `0e275927089a9d04810d483fc6634717d6f7fcd15472a508601cbd5790600f00`；单目标、单 D435i。触发窗 `[0.60,0.66] m/s` 是量测选择器。
- Driver SHA `b15fa2c43497ce076a66f943c3721c51dd25e6672a20bdf912657495cbefe112`；基础运行器与 flight runner hash 记录于 JSON/freeze。驱动器沿用 #377 的 ROS setup nounset 修复。
- 启动后先检查源/安装指纹、有效 planner 参数、spawn、goal、contact overlay 和 action graph；身份不匹配不发目标。
- 项目自加 health/age 门不恢复；保留 PX4 原生预检、EV fusion、桥状态机、epoch/frame/map identity 与官方 EGO collision/watchdog。
- 停止前要求独立 PX4/bridge 读回 landed/disarmed/control-disabled/zero-control。
