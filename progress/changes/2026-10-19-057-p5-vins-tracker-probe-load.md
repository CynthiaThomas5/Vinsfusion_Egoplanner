# P5 VINS 前端计时、定位新鲜度与被动 EKF2 融合诊断

- 任务 ID／日期：057，2026-10-19。
- 对话摘要：[任务对话](../../collaboration/dialogues/2026-10-19-057-p5-vins-tracker-probe-load.md)。
- 修改文件：README.md；progress/CURRENT.md；progress/milestones.json；progress/evidence/README.md；新增本报告及轻量证据报告。
- 行为变化及原因：整理 #128–#132 GPU SITL 诊断，登记 #132 被动 EV 融合结果并明确 P5 仍进行中。#128因缺少run私有probe排除；#129以 telemetry_stale 锁定；#130仅在运行副本对VINS加入tracker计时；#131全分辨率图像observer轮发生clock、传感器、propagation和optimized输出同时接收间隙，单轮不能归因observer；#132移除observer后运行45.051秒，定位健康失败为0、584条optimized和7,723条propagated输出，PX4收到590条VIO并观察到EV position/yaw融合、GNSS aiding全零。桥保持DISABLED，末10秒readiness覆盖率0%，没有控制样本且车辆disarmed。
- 验证类型：回顾已有SITL与诊断构建证据；本轮完成JSON和文件哈希复核、文档与结构检查。
- 命令与环境：原始运行脚本、计时构建脚本、配置和产物由证据报告的SHA-256清单关联；本轮对报告的61个artifact和13个source条目逐一核对SHA-256及大小。
- 结果及证据位置：[轻量证据报告](../evidence/p5-px4-vio-gpu-tracker-profile-20261019-128-132.json)；#132 ULog保留在 artifacts/runs/p5-px4-vio-gpu-tracker-profile-20261019-132/px4_sitl_default/log/2026-10-19/03_32_52.ulg，报告记录其SHA-256。
- 未验证与 PROVISIONAL：#132没有运行mapping、EGO、导航目标、Offboard、arm、轨迹跟踪、障碍课目或10分钟负载。readiness门未通过，P5不通过。tracker有4个样本超过100 ms，#131 observer是否导致间隙未证实；保留的ULog未解析。health门限、相机参数、PX4时钟滤波与canonical VINS源码均未修改。
- 下一步：先用隔离SITL配置延长prestream期限，验证enable服务接受后立即disable的状态机路径、零解锁和零车辆命令；再接入无真值VINS建图/EGO轨迹并完成受控视觉闭环。默认enable服务会自动进入Offboard、arm及起飞，只有轨迹、安全门和停机路径就绪后才进入该路径。
