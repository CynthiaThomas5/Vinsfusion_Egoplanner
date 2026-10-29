# N10.3/#390 综合校准结果

## 结论

16 m 导航 action、60 仿真秒 ACTIVE hold、正常落地和上锁均完成；运行安全收尾通过。该运行没有为 N10.3 提供可用的独立到达、VIO/跟踪、物理步净空或资源/队列校准数据，因此记为 **部分完成／指标 `INSUFFICIENT`**，不通过 N10.3，也不改变 N10 父状态。

## 运行身份与任务

- Run：`n10-20261027-390-integrated-calibration`；SITL 启动后、目标提交前冻结的 runtime contract：679 项，SHA-256 `6885d6b6b0595782839df5ea1d773d8455ee1290a7bcb4688378776bbbe8ed53`。
- preflight 与 goal graph 核对通过；PX4 native preflight、EV 融合与 official EGO 规划分支均保持现有实现。16 m action 返回 `succeeded`，仿真耗时 43.748 s，RTF 0.7416。60 s 诊断保持完成，RTF 0.7445；这不替代 N16 正式 600 s 验收。
- 独立桥/PX4 末态读回为 `LANDED`、disarmed、control disabled，车辆全程保持 disarmed，控制样本为 0。`safe-to-stop.json` 为 true；随后项目 stop 命令退出 0。

## 证据与缺口

- 动态箱体在预定目标后 12 s 触发边界后 0.012 s 获得 Gazebo create ACK；后续同目标替换样条被观察到。但独立真值为空，动态全机净空与完整重规划延迟分析未生成，不能作为重规划或连续净空通过。
- 同一 epoch/map/frame 的 raw/inflated occupancy snapshot 成功读取并校验归档，数组 SHA-256 为 `609c8abd3ed36cbfa728d79f49b0f424cbe3904c587f5b8034fb37944981f20a`，分辨率 0.10 m。快照类别计数：unknown 9,522,476、free 74,643、occupied 2,881、inflated 164,450。
- Gazebo truth recorder 收到 0 个样本；日志显示它访问 `Odometry.twist.twist`，而当前消息提供的是 `Odometry.twist`。因此 source-time 到达复核、VIO/RPE、速度、跟踪与 4 ms 物理步覆盖均无有效输入。`arrival-evaluation-simtime-v2.json`、`odometry-evaluation.json` 与净空报告未生成。
- 原始资源观察报告未生成：`/clock` 订阅 QoS 与 best-effort 发布端不匹配；SIGINT 清理还重复调用了 `rclpy.shutdown()`。资源、RTF 分布与队列指标不能用于定量标准。
- 13 个 raw sphere 请求都因 `radius_m=0` 返回 `invalid_query`；13 个 official EGO radius-zero point 请求被接受。旧查询工具只检查身份，所以将 26 条响应错误报告为 `passed=true`。已明确 raw query API 要求 `0 < r ≤ 2 m`，规划点查询要求 `r=0`，并修正报告与离线 evaluator：只按接受状态、身份和请求几何回显判定采集完整性，`free` 仍是独立服务判定。失败不会控制飞行。
- 接触评估记录 12,577 个接触事件，其中禁止接触 0；这不能替代缺失的物理步净空覆盖。

大件原始数据保存在 `artifacts/runs/n10-20261027-390-integrated-calibration/`。该目录中的 #390 冻结工具及原始错误报告保留，不覆盖重写。修复后的采集器用于独立 #391。

## 修复与验证

- 修复 `tools/debug_truth/record_truth.py` 对 Gazebo protobuf twist 字段的读取；新增纯字段映射测试。
- 修复资源观察器的 `/clock` sensor QoS 和中断清理；观测失败仍只影响离线证据状态。
- 新增 N10 map query contract：raw 请求用显式 0.05 m 球（当前 0.10 m voxel 的半边长），planning 请求保持 radius 0；要求服务接受、身份匹配并回显相同半径和坐标。调整 `config/acceptance.json` 草案说明及 occupancy/acceptance evaluator。
- `python3 -m unittest tools.test_n10_map_query_contract tools.test_n10_acceptance tools.test_n10_occupancy_snapshot`：19 项通过。
- `PYTHONPYCACHEPREFIX=/tmp/n10-pycache python3 -m py_compile ...`：相关 Python 脚本编译通过。
- `bash tools/project.sh test`：455 项通过，navigation action integration 与 official EGO ROS 探针通过。

## 后续

当前仅将 #390 的记录完整归档；N10.3 继续为 `in_progress`。下一子项 #391 复用相同飞行配置与场景，在每条只读观测链路修复后重做综合校准。若 truth/资源/查询输入仍缺失，仍判 `INSUFFICIENT`，不得由观察器触发拒飞、取消或降落。
