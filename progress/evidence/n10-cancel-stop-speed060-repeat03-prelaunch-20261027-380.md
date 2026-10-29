# #380 SITL prelaunch freeze

状态：**容器启动前已冻结**；同一制动协议第3次独立冷启动。

- 新run id `n10-20261027-380-speed060-repeat03`；要求新PX4/Gazebo/VINS进程、新epoch和新goal identity。
- Runtime `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7`；planner `n10_horizon5_speed080_calibration.json`（0.8/0.25/horizon5/official_ego）；spawn `[-8,0,0.3,0,0,0]`。
- 触发窗 `[0.60,0.66] m/s`；停止带/真值/contact/安全末态规则与#378/#379一致。
- #378/#379真值水平路径1.376716m／1.343935m，入口延迟4.844s／4.880s；仅为n=2观察。
- Protocol SHA `5b70e1a7580780d7c1cddddf737fb4a6bd99667890719d1cdccc0fa0cb1a5f37`；prelaunch SHA `778448da1909e77003144ab30f4ba13c146748553a5efa8969be23c8ce12a99a`；driver SHA `1bea033f08529551dd7ec1ca18127854ff0856ce9a239e8dd5bbbc9909857ff4`。
