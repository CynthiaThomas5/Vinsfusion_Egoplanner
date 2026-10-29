# N07 #169 初始 N05 前置检查失败

状态：**FAIL，未进入支架扫描或悬停。** #169 是一次独立 cold-start N07 尝试，按三次连续规则将当前计数重置为 **0/3**；此前 #167/#168 的正向证据保留，但不属于新的连续序列。

## 观测

Run `n07-20261024-169-01` 使用固定镜像、runtime、spawn、wall layout、支架route和既有健康／N05门限。epoch 为 `909adf46d6044c4d9d4b709e094ef04e`。初始只读 N05 live check 以 `--wait-s 150` 等待后仍未收到当前 optimized odometry，错误为 `timed out waiting for current localization/map/bridge/odom/clock state; missing=['odom']; received=['bridge','clock','localization','map']`。N05检查按 fail-closed 拒绝，未产生入口授权。

直接 ROS 状态回读：localization state `4`、`valid=false`、`reason=telemetry_stale`、`good_pairs=84`、`accepted_optimized=75`、`accepted_propagated=1227`、`normalized_cost=0.0877239906`，最后适配器传播源戳为仿真 `13.980 s`；bridge `DISABLED`、`localization_not_tracking`、`armed=false`、`landed=true`、控制关闭。随后一次只读抽样仍可见 raw estimator telemetry 源戳 `222.720 s`、raw optimized odometry `225.360 s`。这说明 raw 流后续可读，但不能解锁已失效的适配器；两个回读并非同步源龄测量，不能据此推断瞬时处理延迟或上游根因。

## 安全与范围

- 初始 N05 未通过；`n05-prescan-ready.json`、支架 trace / `fixture-result.json` 均未生成，因此没有 attached/released gate、任务目标、控制发布或起飞。
- 停止前 PX4 bridge 为 disabled、unarmed、landed。`bash tools/project.sh stop n07-20261024-169-01` 后容器状态 `exited`、退出码0，未见仍运行的该项目容器。
- `Health` 在 TRACKING 后遇 freshness 失败会锁存失效，适配器没有在线解锁路径。这里确认的是 fail-closed 表现；VINS telemetry 何以在该 epoch 失去新鲜性仍未知。健康阈值与控制配置均未调整。
- #090 已记录过一次初始 cold-start `telemetry_stale`，之后另有三个通过的 idle epoch；这只表明相似故障曾间歇出现，不能证明 #169 的根因与 #090 相同。

## 产物与哈希

原始运行目录：`artifacts/runs/n07-20261024-169-01/`。

| 文件 | SHA-256 |
|---|---|
| `n05-before/n05-live-entry-check-error.json` | `136d25bcd9bf88b6f21fb0da4c278a68d2fcde3fef0894bf3e6e3dd1a7d4713e` |
| `n05-before-check.log` | `b2e9213eddad4273584f5397d05204d0037441c21c6a2f99db6658686c3f33d5` |
| `n05-run-inputs.json` | `41c729342b6d37b98a06f1492fa3b0bc28d92e30adea35150d6a17ab358d6b8d` |
| `runtime-contract.json` | `856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb` |

下一项 #170 继续相同配置与门限的新冷启动；若前置检查再次失败，先保存同时段 telemetry、clock、raw／adapted odometry 与 health 状态，再决定是否存在本范围内的修复路径。
