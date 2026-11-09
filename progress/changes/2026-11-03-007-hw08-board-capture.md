# HW08 板上采集与记录负载调查

对话：[HW08摘要](../../collaboration/dialogues/2026-11-03-005-hw08-body-time.md)。执行模式：用户要求持续完成前三项，最终装机包络另列；不扩大到真实EV/控制/飞行。

- 增加只读board recorder、工作站MAVLink解码/带Nano时间的串口转发、现有位姿日志配对分析，以及显式单独CMake构建的原生IMU/位姿CSV诊断。没有新增控制发布者。
- hardware.sh清除pipefail下head/awk提前关闭输入导致的SIGPIPE退出；采集/SDK配置不变。
- 原诊断Python解码占Nano约63.5%单核；隔离nativeCRC本身18.2倍基准未解决真实失效。把解码迁到工作站使Nano串口进程约6.6%；run08仍源龄失效。run06/07/08全部否定结果保留，未改源龄/接收龄门限。
- 只变VINS_OPENCV_THREADS=1的run09/10，独立有效跨度约377.35/415.45s，包含三轴动作；日志最大优化源龄约0.694s，固定门限0.868306s。原二进制哈希与HW04一致。将opencv_threads=1存入硬件VINS配置，生成session.runtime并绑定设置哈希，启动读取并核对后导出环境变量；不把运行环境键冒充VINS YAML参数。
- run09抬头阶段FC/VINS差异明显，用户确认可能相机单独动/松动，禁止用于标定；用户重新固定后run10补测。run11原生订阅者虽仅约2.8%CPU，新增采集组合仍源龄失效；不能把低负载两次成功外推为全部负载稳定。
- 相机原始gyro存在静态零偏。一次即时说明把未扣偏的22°与FC14°直接比较，随后已明确纠正：独立baseline扣偏后约15.5°/13.7°。原始数据不修改，零偏仅用于离线对比。
- 继续用独立静止倾斜姿态检验安装旋转；完整rig暂未通过，不能用拟合改善有限或诊断报告关闭安装出口。

定向验证：tools/test_hw08_board_clock.py 4项、tools/test_hw08_serial_relay.py 2项、tools/test_hardware_rig.py 4项通过；原生诊断ARM CMake构建通过。完整原始运行/哈希见artifacts/runs/hw08-board-20261103-{02,06,08,09,10,11}及[板上证据](../evidence/hw08-board-20261103.md)。结构检查只表明结构一致，不代表实测通过。

当前仍实施中；最终安全终态与安装结论将补入证据/CURRENT。
