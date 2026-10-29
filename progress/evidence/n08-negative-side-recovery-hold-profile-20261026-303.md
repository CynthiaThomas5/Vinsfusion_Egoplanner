# N08 负侧视回收中立保持 profile（#303 静态验证）

状态：profile 与 runner 接口静态验证通过；尚无 SITL 结果。

新增 `n08_overhead_free_sector_with_negative_side_recovery`。它逐段保留 #302 的负 Y 侧视 profile，在 yaw=0、z=1.0 m 回中段之后、原 z=0.5 m 下降前，插入 15 秒静止保持。其余平移、上视、正侧视、负侧视、回中和下降 stages 完全相同。

这一受控变更针对 #302 的记录：侧视与回中已完成，但 cost 在开始垂直回收后达到1.025847并触发原有1.0门限。#303 检验中立恢复是否让 VINS 在开始下降前回到门限内。未知判据、N05/N08 包络、速度、制动配置和 cost 阈值都未调整。

验证：`python3 -m unittest tools.test_preflight_scan` 37 项通过；JSON parse、`bash -n tools/run_n05_preflight_layout.sh`、`python3 tools/project_status.py` Structure/design PASS、`git diff --check` 均通过。静态检查不代表 SITL。

下一步：使用新冷启动跑此 profile，确认 scan、fixture detach/landed、同身份 post-release/current-area N05 与 N08 forward corridor/start/terminal hold raw-map 查询；通过后才运行 motion-cancel。
