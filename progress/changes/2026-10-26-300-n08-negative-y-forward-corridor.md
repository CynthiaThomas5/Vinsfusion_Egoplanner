# #300 N08 侧向 unknown 前置拒绝

## 实施范围

使用一个新的 cold start 和既有 `n08_overhead_free_sector_view` 支架 profile 重做 N05 观测；保持配置门限和 trial source 不变。

## 结果

支架路线到达 15/15，fixture model 已脱离并从 Gazebo 删除。记录有定位状态 warning，且 helper exit 2；最终定位有效、身份连续、post-release N05 `diagnostic_pass=true`。post-release 和 mission current-area online/offline N05 均在同身份下通过五阶段。40.002 秒 read-only preflight 通过。

N08 0.6 m forward corridor 与 0.5 m 候选取消包络在预启用地图检查中被拒，首个 directional sphere 有 66 unknown；start 与 terminal hold 各有 58 unknown。只读 cell audit 显示该批 unknown 位于 map ODOM `y=−1.05m` 薄层、处在 N08 固定球形包络内。mission 没有发 goal/enable/service/control；PX4 独立读回 landed/disarmed、bridge disabled、control0。容器按项目流程停止 exit 0。

完整证据：[报告](../evidence/n08-negative-y-forward-corridor-refusal-20261026-300.md)、JSON 及 `artifacts/runs/n08-cancel-highspeed-prescan-20261026-300/`。

## 下一步

#301 只把 N05 观测 profile 换为既有 `n08_overhead_negative_side_view`，针对量得的负 Y unknown 薄层尝试观察；不改变任何 N05/N08 threshold 或 trial 参数。
