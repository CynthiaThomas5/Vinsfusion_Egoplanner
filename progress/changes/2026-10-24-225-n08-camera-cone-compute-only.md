# N08.2o #225：fresh map 与视场内 compute-only

## 假设与判据

- 复用 #221 已完成的 N08 15 阶段顶板观察路径和同一 `wall_box_column` 场景；N05、EGO、raw unknown 与地图身份门限不变。
- fresh post-release/current-area online 与 offline 门禁、同一 epoch/map 下起点／目标机体球、目标 terminal-hold 球、连续路径扫掠和顶板 raw occupancy 均需通过；任一 unknown 就不得使用该候选。
- 只有 bridge 输入隔离且候选门通过时才跑 compute-only；要求 live EGO READY、取消确认、桥继续 hold、最终 landed/disarmed。本项不执行 XY。

## 实施与结果

- Run：`n08-20261024-225-camera-cone-compute-only-01`。N05 scan profile 完成 15/15；运行摘要 `diagnostic_pass=true`，post-release N05 online/offline 接受且 identity 相同。
- 支架 helper 原始结果仍为 `failed`，错误是 `fresh DISARMED status is required for every fixture command`。错误未删改；summary、post-release 和 mission-time fresh readback 均确认车辆 landed/disarmed、fixture 已脱离且模型不存在。
- 旧候选 `[+0.8,+0.3,0]m` 在新图的 terminal-hold 球含 2 个 unknown，故未用它。对同图候选再筛选后，选 `[+0.5,+0.2,0]m`（0.539 m，camera bearing 20.11°）：起点／终点 body sphere、终点 0.980618 m terminal-hold sphere 均全 free，22 次 continuous-line 查询均通过；顶板附近同一 ROI 有 891 个 raw occupied voxels。起点 terminal-hold sphere 仍有 42 unknown，作为限制保留。
- mission-time N05 current-area online/offline 均接受，与 post-release 保持同 epoch/map。
- `flight.json` 的 runner 结果为 `PASS`：观察到该 goal/epoch 的 READY，bridge 未订阅 `/position_cmd` 而订阅隔离输入；cancel 接受且 action 状态为 canceled，取消后 hold 满 2.0 仿真秒，最终 landed/disarmed，无 clock regression。N08 专用 evaluator 12 项检查全部通过。
- 最初 `project.sh mission` 外层返回 1：通用 `evaluate_odometry.py` 因 compute-only runner 未保存 `localization_quality_history` 抛出 `KeyError`。修复 runner 以供后续运行保存该历史；通用 evaluator 对旧记录将缺失历史明确记作 unavailable/null；mission runtime 先写 N08 专用 evaluation。用原始 run 输入的 byte-identical scratch 副本重放 odometry evaluator，返回 0；报告标记 `localization_quality_history_available=false`，没有伪报“0 个无效状态”。
- 按项目流程执行 `bash tools/project.sh stop ...`，exit 0，容器 `Exited (0)`。

## 验证

- `bash -n tools/mission_runtime.sh`：通过。
- 对两个改动的 Python 文件做 AST 语法解析：通过。
- `python3 tools/evaluate_n08_compute_only.py .../flight.json`：12 项检查通过。
- odometry evaluator 在只读 scratch 副本运行：exit 0；原始输入哈希记录在 evidence JSON。
- `git diff --check` 与结构检查在本轮结尾执行并记录。

## 范围限制与下一步

本项只证明同图准入、EGO 曲线 READY、隔离输入下取消／hold／落地。没有执行水平轨迹，也没有测得响应延迟、可用减速度、停止距离或运动跟踪偏差；N08 仍需三次独立冷启动的实际低速运动／制动和预算回填。详细结果与 SHA-256 见 [`n08-camera-cone-compute-only-20261024-225.json`](../evidence/n08-camera-cone-compute-only-20261024-225.json)；odometry 描述报告见 [`n08-compute-only-odometry-20261024-225.json`](../evidence/n08-compute-only-odometry-20261024-225.json)。
