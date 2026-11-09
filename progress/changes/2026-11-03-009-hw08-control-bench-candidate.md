# HW08 板上近似候选与同桥硬件control路径

对话：[HW08摘要](../../collaboration/dialogues/2026-11-03-005-hw08-body-time.md)。用户要求完成前三项，后明确柔性板无替代底座并接受近似板上结果；原严格安装出口仍未通过。

实际改动：

- 同一Px4BridgeNode支持hardware_system control配置，复用原OffboardSupervisor/显式使能服务，未增加第二控制发布者。ev_only仍无三个控制发布者/使能服务。硬件无SDF或/clock依赖。
- 完整T_BI先换算body姿态，再进行局部yaw/原点配准，避免光学IMU右轴当机头；EV采用arbitrary-heading FRD。硬件source/sample/send时间采用Agent系统epoch、不重复加offset。新增硬件遥测源龄/接收龄、Timesync接收龄/协议、指令源龄/接收龄以及倒退/epoch门控，沿用原控制状态机。
- 实际rig保存近似bench候选及失败的独立验证数值，airframe T仍null/control_usable false。候选使用此前(0.20,0.01,0)m平移和受前向关系约束的静态倾斜拟合，未宣称刚性/飞行资格。
- 原生CSV/独立静止姿态分析补充至tools/diagnostics；COLCON_IGNORE隔离显式CMake诊断构建，不添加假ROS包。
- Nano定向测试发现vio_ego_bringup.py源文件仍旧（缺rig_config参数）；备份prior源后部署本仓库已有真实rig支持的canonical版本，并用fresh build-base重建唯一bridge包。此前参数TypeError保留，不作为通过。

验证：主机10组85项定向检查通过（控制14、坐标19、VIO7、时钟23、HW08变换/实测clock8、relay2、board4、static2、rig4、VINS生成2）。ARM bridge定向构建、实际安装模块与隔离domain83节点检查见artifacts/runs/hw08-control-20261103-03。域83合成输入不代表实际PX4融合/控制；真实输出始终未启动。

运行/局限见[板上证据](../evidence/hw08-board-20261103.md)和[软件/时间证据](../evidence/hw08-body-time-20261103.md)。yaw-only规划杆臂仍是低倾角近似；run02实测姿态下几何差约最大3.69cm，不是外部跟踪误差。原严格安装和新增订阅负载稳定性仍未通过，最终包络/真实EV融合/控制/飞行留后续相应模块。

最终节点结果：使用canonical近似矩阵数值的合成control fixture为1164EV；使能前715EV/控制0，使能后40mode/40setpoint/1模式请求；独立ev-only真实未测rig0EV、合成518EV，三个control publisher仍0。7安装模块hash、Nano rig4/VINS生成2通过。最终结构/diff通过，终态图无fmu/in发布者、USB无占用、.runtime空、rmem212992。

停止原因：完成用户调整后的近似板上交付；原严格刚性安装/最终包络仍受外部安装条件限制，不推进下一模块或真实控制。下一项唯一为刚性最终安装后重新量测与对应验证。

最终补齐硬件control来源隔离和Agent同步/零手工offset输入约束，使用final-build重新构建并重跑两个域83节点检查（control-node-final.log/ev-node-final.log）。主机colcon list首次写根log目录权限失败，改用本轮artifact的--log-base后成功，独立CMake诊断目录扫描为空；未修改用户log权限。
