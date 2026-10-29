# #302 新增负 Y 侧视 N05 观察 profile

## 修改

- 在 `config/components/simulation/preflight_scan.json` 基于 #300 已完成并取得 post-release 五阶段 N05 准入的 `n08_overhead_free_sector_view` 新增一个 profile：只增加 yaw−π/2/pitch0 侧视 16+18 秒和 yaw 回中 12 秒，再继续原下降／回收阶段。
- 同步 Python fixture runner 和 shell N05 runner allowlist。
- 增加静态测试，逐项比对基线路径和新增视角顺序。
- 未改 N05/N08 thresholds、车辆包络、速度、goal 或制动配置。

## 验证

`python3 -m unittest tools.test_preflight_scan` 36 passed；JSON parse、`bash -n tools/run_n05_preflight_layout.sh`、`python3 tools/project_status.py` Structure/design PASS、`git diff --check` passed。静态结果不代表 SITL。

下一步：使用 #302 新 profile 做新冷启动；只在 N05 post-release/current-area online/offline 和 N08 trial raw corridor/hold 查询都通过后启动取消制动 mission。
