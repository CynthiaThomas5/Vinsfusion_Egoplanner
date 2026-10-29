# N08.2ai #246：定位新鲜度诊断与低速曲线准入

## 结果

#245 的 PX4 HRT／ROS `/clock` 时间域问题在同配置冷启动 #246 中没有复现：266/266 个 bridge 时间样本有效，HRT 与 ROS 时钟差为 −8 至 +16 ms，零时钟回退；304/304 个 LocalizationStatus 样本有效。此次没有触发 telemetry-stale 锁存，因此不能把 #245 的偶发锁存归因于 PX4 时间参考，也没有证据证明其调度根因已修复。

N05 的 16/16 个支架阶段完成，释放后与当前区 online/offline 准入均以同一 epoch/map 接受。fixture helper 仍报告 `fresh DISARMED status is required for every fixture command`；保留该警告，并以独立读回确认车辆 DISARMED、landed/at-rest、bridge 禁用且 fixture 不在 Gazebo 中后才继续 compute-only。

compute-only 的 READY、cancel、bridge hold、落地和控制隔离评估为 12/12 通过。这只证明轨迹生成与取消/保持流程，不是 N08 通过。曲线证书仍拒绝执行：x 轴导数控制上界为 0.09260 m/s，高于 0.07885 m/s 单轴限值；起点 hold 球有 100 个 unknown。向量速度上界 0.10205 m/s 低于 0.15 m/s 向量限值；地图 freshness、start/end body、end hold 与 44/44 连续扫掠通过。unknown 位于地面以上，集中在起点侧负 Y 薄带。未执行 XY，也没有制动距离或减速度证据。

末态 fresh readback：DISARMED、landed 且 at-rest、bridge `LANDED`/control disabled、localization valid、fixture absent。`tools/project.sh stop` 后容器 `exited`, exit code 0。#245 的触发链仍未查明；未来单次运行可能因新鲜度门安全拒绝，但这不表示 PX4 时间对齐继续阻塞 N08。

## 验证与产物

- 定向定位健康测试：14 项通过；ROS 构建：17 个包完成。
- N05/compute-only/evaluator：post-release 与 current-area 同身份准入、任务终态及隔离检查通过；不替代曲线证书或实际运动。
- 主证据与 SHA-256：见同目录 `.json` 报告；完整运行记录位于 `artifacts/runs/n08-20261024-246-localization-freshness-diagnostic/`。
- 安全读回与最终停止状态：`artifacts/runs/n08-20261024-246-localization-freshness-diagnostic/final-safety-readback.json`。

## 下一步

继续 #247：在 #246 通过的慢回程扫描配置上只增加负 Y 方向观察、停留和回中；检查同 run 起点 hold unknown 是否清零。保留原速度与地图门，证书通过之前不执行 XY。
