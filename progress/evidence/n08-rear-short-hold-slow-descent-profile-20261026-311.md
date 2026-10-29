# N08 #311：rear short-hold slow-descent profile（静态准备）

状态：profile 与 runner 接线已静态检查；尚无 SITL 结果。

- 以已到达 yaw=−π rear-facing 视角的 `n08_overhead_free_sector_negative_y_rear_short_hold` 为基线，新增 17 阶段 profile。
- 唯一变化是 yaw 回中后 index 14 的垂直下降时间由 8 s 改为 12 s。rear dwell、航向、观察位置、其他路线和所有健康／地图／N08阈值不变，总 profile 时间增加 4 仿真秒。
- `n08_overhead_free_sector_negative_y_rear_short_hold_slow_descent` 已加入 probe runner 与 N05 host wrapper 的合法选择。profile 回归检查逐阶段确认只有 index 14 的 duration 变化。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_preflight_scan`：42 项通过。
- JSON parse、`bash -n tools/run_n05_preflight_layout.sh`、`python3 tools/project_status.py`（Structure/design PASS）及 `git diff --check` 通过。结构检查不代表 SITL。

修改文件 SHA256：

- `config/components/simulation/preflight_scan.json`：`78e4001fc13510440c0c2ef65bdb90611e8a5554629ad51ffac116ad26b55f9e`
- `tools/probe_preflight_scan.py`：`f6088e2795a26fe631de41c2dc21c467a66f3dda4dbb5a0ae45e7ee91639cae8`
- `tools/run_n05_preflight_layout.sh`：`563c5e7a4c039b1a48b47cf29e8388d7bf6ba1c45cf781d25a3835aebfbaff7f`
- `tools/test_preflight_scan.py`：`0d9aaf714dab77261c8b5642416d0ac22900173b81e942309f62dbb9aa326ffe`

机器摘要：[JSON](n08-rear-short-hold-slow-descent-profile-20261026-311.json)。下一步新 cold-start N05 scan 使用 run id `n08-cancel-highspeed-prescan-20261026-311`；完整 scan 与同身份 post-release N05 必须通过，才继续实时 N08 几何检查。
