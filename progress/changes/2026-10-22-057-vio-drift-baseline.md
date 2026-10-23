# 原始 VINS 整段漂移基线

[用户约定](../../collaboration/dialogues/2026-10-22-057-vio-drift-baseline.md)。

## 实施前声明

- 问题：现有到点最小误差不能表示整条里程计轨迹；旧 `evaluate_vins_motion.py` 在整条轨迹上拟合刚体变换，不满足本次只在初始化对齐的约定。
- 实验：固定当前 room／16m 路线、源码与参数，增加原始 VINS 旁路只读记录和离线评估。预期输出完整飞行段位置／yaw 误差及缺失数据，而不是预先要求误差很小。
- 对齐：使用 preflight 最后仿真时刻之前 1 秒处的最后一条原始 VINS 状态，最多早 150ms；源时刻插值真值、依据单一 SDF 安装偏移转换到 IMU，固定一个 SE(3)，尺度 1。参考必须早于 PRESTREAM；没有全轨迹／分段／尺度／时间偏移拟合。
- 评估段：桥 PRESTREAM 至 LANDED，包括起飞、导航与降落；记录终点最后有效样本距 LANDED 的时间。初始参考误差仍会影响全段结果，不宣称绝对无误差的坐标标定。
- 数据：原始帧与 epoch 必须一致、源戳严格递增；真值插值跨度不超过 40ms（50Hz 期望周期的两倍）。覆盖率单独报告配对样本比例及时间支持；200ms VIO 支持间隔仅为统计定义，不改在线健康门。
- 通过定义：一次独立冷启动、原任务正常落地上锁，有完整可追溯报告和曲线。精度只测量，不设置事后通过阈值；不升级 P0–P6／A–H 状态。

## 文件和验证

- `tools/diagnostics/record_alignment.py`：同一只读节点另订阅 session 中的 raw VINS 优化里程计，保留 frame、child frame、epoch 和源时间；适配输出继续单独记录。
- `tools/debug_truth/evaluate_odometry.py`：只读离线评估，输出 JSON／CSV，可选 PNG；检查原始与适配同源时刻位姿是否一致。
- `tools/test_odometry_evaluation.py`：合成漂移、安装偏移、缺口、重置、参考与终点检查。单元测试不是 SITL。
- `tools/mission_runtime.sh`：成功任务完成既有 9 项检查后，生成额外里程计报告；没有新增控制发布者。
- `docs/running.md`：说明额外 JSON／CSV、离线绘图命令、对齐与覆盖率定义；不修改既有入口命令。
- 本地首轮 7 项单元：一个精确浮点相等断言失败；时间覆盖累计改为整数纳秒，并显式扣除真值长缺口后通过。

## 实际验证结果

- 静态：`bash -n tools/mission_runtime.sh`、`git diff --check`通过；`python3 tools/project_status.py`结构检查通过，后者不作为飞行证据。
- 单元／集成：服务器 `bash tools/project.sh test` 退出0，149项回归＋真实ROS action集成通过，250Hz时钟／活动action的最大pose接收龄0.053s。新增加的7项为合成评估器单测，不冒充真实轨迹。
- 构建：没有修改ROS源码／参数／第三方／binary，只增加观察订阅和离线工具；没有不必要地重建ROS或PX4。运行合同与#054–#056一致。
- SITL：原空闲GUI正常停止；`bash tools/project.sh sim vio-baseline-20261022-057-01`、`mission`、确认落地后`stop`均退出0。第一次新冷启动即完成，原9项qualification全通过，flight为PASS、正常落地上锁。停止后容器exited／exit0，无运行中的项目会话。
- 误差：85.144仿真秒，1290个原始VINS样本全部配对，原始与适配位姿1290对完全一致；时间支持率99.9154%。位置RMSE／最大／最后为4.557／9.014／8.772cm；yaw RMSE／最大为0.2943°／0.5095°。没有修改任何精度／健康门限。
- 离线复算：真实数据在本地运行 `python3 tools/debug_truth/evaluate_odometry.py artifacts/runs/vio-baseline-20261022-057-01 --plot`，查看PNG确认轨迹与误差曲线可读。主机与服务器数值差异不超过2.22e-16，输入及评估源码哈希一致；保留服务器主JSON，复算记录另存checks。固定镜像没有Matplotlib，不安装新依赖，不修改运行镜像。
- 运行期ROS图快照无真值话题订阅；所有PX4控制输入发布者均为唯一桥节点。真值只由隔离Gazebo订阅者写文件，离线程序不发布ROS／Gazebo数据。
- 归档时第一次复制session子目录因本地父目录不存在返回11，创建父目录后重传成功；不影响已完成SITL或原始数据。原生ULog保留服务器并记录哈希，其余轻量日志／轨迹已回收。

详见[测量报告](../evidence/vio-drift-baseline-20261022-057.md)与[机器可读证据](../evidence/vio-drift-baseline-20261022-057.json)。CURRENT更新，小目标完成；保留之前的全部未提交修改，milestones阶段状态不变，未提交／推送。

## 局限与下一步

一次约85s仿真，不是5分钟／多场景／实机验收。可以确认该路线存在逐渐累计的定位误差，不能证明根因或回环效果。真机Nano系统未改动，没有安装依赖或停用桌面。按用户要求在此小点完成后停止推进，等待用户选择下一项。
