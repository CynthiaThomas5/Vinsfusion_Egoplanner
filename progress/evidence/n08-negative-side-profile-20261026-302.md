# N08 负 Y 侧视观察 profile（#302 静态验证）

状态：profile 与 runner 接口静态验证通过；尚无 SITL 结果。

在 `config/components/simulation/preflight_scan.json` 新增 `n08_overhead_free_sector_with_negative_side_view_profile`。它逐项保留 #300 的 `n08_overhead_free_sector_view` 15 段路线，在原 yaw 回中后加入 yaw −π/2、pitch 0 的 16+18 秒负 Y 侧视，再 yaw 回中 12 秒，然后使用原来的下降、回收、稳定阶段。唯一观察变量是新增加的负侧视。N05/N08 unknown 检查、全机／tracking 包络、速度、制动、任务目标和地图阈值均未改变。

`tools/probe_preflight_scan.py` 与 `tools/run_n05_preflight_layout.sh` allowlist 同步加入该 profile，新增 profile 定义测试验证基线路径完全一致、侧视目标和回中位置准确。

验证：

- `python3 -m unittest tools.test_preflight_scan`：36 项通过。
- `bash -n tools/run_n05_preflight_layout.sh` 与 `python3 -m json.tool config/components/simulation/preflight_scan.json`：通过。
- `python3 tools/project_status.py`：Structure/design check PASS；该检查不代表构建或 SITL。
- `git diff --check`：通过。

下一步使用新冷启动验证 18 段 profile 的定位健康、夹具回收、同身份 post-release/current-area N05，以及相同 frozen N08 corridor/start-hold/terminal-hold gate。只有 raw map 全 free 后才执行 motion-cancel。
