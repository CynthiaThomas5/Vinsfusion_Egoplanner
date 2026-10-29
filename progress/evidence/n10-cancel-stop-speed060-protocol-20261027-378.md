# N10.3 #378 caller-cancel braking protocol

状态：**SITL 启动前冻结**。#377 在相同 runtime/planner/spawn 下，实际 PX4 水平速度峰值为 `0.647896 m/s`，EGO 指令峰值为 `0.715213 m/s`；`[0.70,0.80] m/s` 未命中，但离线按同目标／epoch READY 指令关联找到 110 个 `[0.60,0.66] m/s` 候选样本。

唯一变量为 PX4 水平触发窗 `[0.60,0.66] m/s`。运行配置、单程目标、spawn、observer、PX4停止带与运行时版本保持不变。窗口只选择近峰值制动样本，不是速度限制或验收阈值。首个历史候选为 `0.601296 m/s`（仿真时间 `349.528 s`），下界约为实测水平峰值的 `92.6%`。

完成样本需满足：触发速度被实测到；caller cancel 被确认；出现不同 EGO trajectory id；PX4 水平速度 `<=0.03 m/s` 且竖直绝对速度 `<=0.05 m/s` 连续 1 仿真秒，PX4 样本间隔 `<=0.20 s`；真值空档 `<=0.04 s`；contact observer 完整且零违规接触；独立终态 landed/disarmed/control-disabled/zero-control。失败或缺数据按原样保留。

固定配置：horizon 5 m、`max_vel=0.8 m/s/axis`、`max_acc=0.25 m/s²/axis`、`official_ego`；spawn `[-8,0,0.3,0,0,0]`；目标 `+16 m/+0.10 m/+0.20 rad`。

协议 JSON：[n10-cancel-stop-speed060-protocol-20261027-378.json](n10-cancel-stop-speed060-protocol-20261027-378.json)，SHA-256 `ed94789c999dec92159ab2390a0197923b155fa59f22fbb1488dc23adb6b917d`。Prelaunch：[n10-cancel-stop-speed060-prelaunch-20261027-378.json](n10-cancel-stop-speed060-prelaunch-20261027-378.json)，SHA-256 `f62e349867805f37585f43a57767f13e8bfb94cd16eebf131ccb57ae47de8a05`。Driver `b15fa2c43497ce076a66f943c3721c51dd25e6672a20bdf912657495cbefe112`。Runtime source/install SHA `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7`。
