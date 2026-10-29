# N10.3 #380 braking repeat 3 of 3

状态：**SITL启动前冻结**。#378/#379在相同runtime和协议下均取得完整caller-cancel样本，真值水平路径分别为1.376716m、1.343935m，停止带入口分别4.844s、4.880s。#380以新的Gazebo/PX4/VINS冷启动重复原协议，为有限样本总结补第三点；不改任何运行或测量配置。

触发窗仍为 `[0.60,0.66] m/s`，stop band、truth覆盖、contact和终态读回标准不变。三次样本不构成通用制动保证或最终接受阈值。

Protocol SHA `5b70e1a7580780d7c1cddddf737fb4a6bd99667890719d1cdccc0fa0cb1a5f37`；prelaunch SHA `778448da1909e77003144ab30f4ba13c146748553a5efa8969be23c8ce12a99a`；driver SHA `1bea033f08529551dd7ec1ca18127854ff0856ce9a239e8dd5bbbc9909857ff4`；runtime SHA `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7`。
