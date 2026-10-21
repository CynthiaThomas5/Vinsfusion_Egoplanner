# 工程工具

日常只需`project.sh`：fetch、build、test、sim、mission、stop、export，见根README。build_runtime／sim_runtime／mission_runtime是容器内部实现，不应另起第二套控制栈。

必要公共工具：固定依赖获取、配置／场景生成、PX4空状态隔离、IMU落稳与物理契约、启动参数审计、运行fingerprint、前检和任务结果核验。`run_vio_ego_flight.py`只调用导航action及桥服务，不发布PX4设定点。

`diagnostics/`记录规划样条与估计状态；`debug_truth/`只读真值记录及离线到达／净空评估。debug_truth不作为在线定位／地图输入。

`test_*.py`和已有probe／fault工具保留为有意义的单元回归、epoch／时钟／输入断流、坐标及消息接口验证，不随默认启动执行。`run_vio_no_goal_hover.py`复用同一飞行探针进行正式无目标悬停检查；debug_truth飞行工具仅保留给隔离基线，不能接入默认视觉组合。

历史一次性启动器、未采用补丁和试验参数已移出活跃目录，恢复位置及哈希记录在`dependencies/retired-code-20261021.json`。开发测试与SITL结果各自记录，不以结构检查替代运行证据。
