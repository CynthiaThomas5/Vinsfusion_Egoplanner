# N08 负 Y 侧视短驻留 profile（#304 静态准备）

状态：静态 profile 和选择器验证通过；SITL 尚未运行。

- 新 profile `n08_overhead_free_sector_negative_side_short_dwell` 复制既有负 Y 观察路线，只将 yaw −π/2 到位后的同目标静态观察段由 18 s 改为 8 s。此前 16 s 到位／转向段、回中、下降和其它路线时长均保持；N05／N08 的 cost、unknown、时间、速度、机体和跟踪门限均未改。
- `python3 -m unittest tools.test_preflight_scan`：38 项通过；新增测试核对 profile 与 #302 基线逐项相同，仅观察段时长不同。
- `bash -n tools/run_n05_preflight_layout.sh`、配置 JSON 解析、`python3 tools/project_status.py` 均通过。结构检查只说明项目结构一致，不是构建或 SITL 结果。
- 有效 profile 仍需一次全新 SITL：如果扫描健康、fixture removal、同身份 post-release/current-area N05 与前向 corridor/start/terminal hold 全部通过，runner 才可按配置进入 N08 motion-cancel。任一门拒绝则保留运行失败并安全停止。

受影响文件 SHA256：

- `config/components/simulation/preflight_scan.json` `28bf8ec726e2645b2bb66a22342e9fd067fdebd55e3c6253830db718c570c70b`
- `tools/probe_preflight_scan.py` `18b45552449002d6248b4d07c6865b389f63e0f01112f568dac2c50a1cae1006`
- `tools/run_n05_preflight_layout.sh` `6e7da0cbc767a599e4c7797481a10666bed9c0e459c536a00b97933ba71314f0`
- `tools/test_preflight_scan.py` `41c2c5df6e1b88383024ac1b0f8ef7c8fccf2e6ec3b2a7b7fb719a3b4cc86e4c`
