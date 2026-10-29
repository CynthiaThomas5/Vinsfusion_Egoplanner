# N08.2e #215：候选 compute-only 前置扫描因 VINS 遥测 stale 中止

## 结果

**未进入 N05 释放后准入或 compute-only。** Run `n08-20261024-215-compute-known-free-01` 的未武装全机支架扫描在第 5/12 阶段失败，最终 localization status 为 `state=4, valid=false, reason=telemetry_stale`。该失败发生在 VINS 定位健康链；不是 PX4 HRT 与 `/clock` 时间参考判错的证据。

N07 的累计 3/3 无目标悬停仍由 #198/#200/#204 支持，按用户要求不要求连续且不复测。PX4 HRT 时间参考修复和 ground SITL 读回仍由 #206/#207 支持；#215 没有起飞，不能对 PX4 airborne 时间门作新结论。

## 遥测时间线

- 当前定位健康配置 `config/components/localization/health.json` 对 VINS `telemetry` 的最大 source age 为 0.30 s，最大 receipt age 为 0.50 s。
- `fixture-vins.jsonl` 中相邻 source stamp 最大间隔为 0.728 s（260.536→261.264）；另有 0.460 s（204.240→204.700）及 0.332 s（204.700→205.032）。这些间隔超过 0.30 s source-age 门限。
- 同 run 的 raw odometry source stamp 最大间隔为 0.792 s（260.868→261.660），并有 0.596 s（204.568→205.164）。遥测和 odometry 记录均显示有输入间隔，但当前记录不能区分 VINS 发布、DDS 传递、observer 接收或 `/clock` 进度各自的贡献。
- 对照历史 N08 支架记录：#211 与 #213 的 telemetry 记录也各有超过 0.30 s 的间隔（分别最大 0.660 s、0.396 s），但扫描 trace 全程采样为 `TRACKING`；#211 helper 曾报定位状态变化，而最终状态又恢复为 `TRACKING`。这说明“source stamp 间隔超过 0.30 s”本身不足以单独解释 #215 的锁存。
- #215 trace 的最后样本仍为有效 `TRACKING`；随后 fixture result 锁存为 `telemetry_stale`。`vio.log` 记录 mapping gate 在 simulator time 约 204.9 s 关闭，但 fixture trace 没有记录首次 LocalizationStatus 转换的精确时刻，telemetry 文件也没有 callback receipt 时间；触发点仍需补齐。

因此可以确认 #215 的最终定位状态因 `telemetry_stale` fail-closed，且同 run 有较大的 source stamp 间隔与之时间相近；但**source gap 与 stale 的因果和首个故障环节尚未证明**，也不能归因于 PX4 时间对齐。现有证据不支持放宽 0.30 s 定位 source-age 门限。

## 安全收尾

`fixture-result.json` 记录扫描清理已尝试并验证 fixture detached，最终 land detector 为 landed 且回执新鲜；所有 PX4 状态样本均为 DISARMED，最终 `final_landed=true`，fixture 已从场景移除。`tools/project.sh stop n08-20261024-215-compute-known-free-01` 返回 0；本次回读没有发现活动的该 run 容器。

## 后续风险与下一步

非连续验收是合理的：#198/#200/#204 是三次相互独立且各自满足出口的冷启动；后续失败不会清零这三次，也不会要求重测。每个新运行内部仍须满足当前 freshness 与安全门。PX4 HRT 时间参考另有 #206 修复和 #207 ground SITL 读回，#215 没有证据表明它回归。

N08 不是被 PX4 时间参考问题永久卡住：#212 已完成固定 hold，#213 的 release/current-area N05 gate 已 fresh 通过并进入 compute-only；#213 后续因 planner 没有产出 READY 曲线而未通过。另一方面，#215 的实际定位 stale 会拒绝本次 N05 放行，如果重复就会继续挡住依赖该准入的运行，不能绕过。

N08 保持 `in_progress`。N08.2f #216 在受控的未武装扫描窗口同步记录 VINS telemetry/raw odometry 的 source stamp、接收时刻与 `/clock`，并记录 localization status 首次转为 stale 的时刻。全量 `probe_vio_stream_freshness.py` 曾作为可选 observer 未启动项参与 #192 的负载对照，因此这次用只订阅关键时间线的轻量诊断 recorder，且仅作诊断、不作为飞行验收。先区分发布间隔、传递／接收延迟和仿真时钟推进，再决定是否需要代码修复；不能重测 N07 已通过项，也不能跳过 N05 新鲜准入。

原始产物：[`artifacts/runs/n08-20261024-215-compute-known-free-01/`](../../artifacts/runs/n08-20261024-215-compute-known-free-01/)。关键 SHA-256：

- `fixture-result.json`: `2c0fe258faa9b4a9203a351d4f0785322890b3489744fe1d101416b82611fc8d`
- `fixture-vins.jsonl`: `8889e6c0762a44306b0d0234ef3d7b5521e36cb9d9ad1cf9a08ab7c69ecffd54`
- `fixture-odometry.jsonl`: `c373b063f05b98d9dafd28382026b49ec9fdb67a1c6b02082b7eedafd2739f08`
- `vio.log`: `fd21e0211b1c7e40e3dd4ed0675cd57432ee6942b465c9fcffa4898125be951e`
- `runtime-contract.json`: `ea86c8dbd1187c3b1a9bff476cc915ae02b3649b9d702c74f00dde0e1e363c3e`
