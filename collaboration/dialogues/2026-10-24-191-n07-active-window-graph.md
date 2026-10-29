# N07 #191 对话摘要：ACTIVE 后启动只读 graph 采集

## 约束

- 延续用户授权的 N07 Goal 完成模式；仍要求固定版本 3 次连续独立冷启动全部通过。
- 镜像、runtime、spawn、wall layout、support profile、N05/health 门限与 30 秒 no-goal hover 均不变。
- 唯一改变是只读 ROS graph recorder 的开始时刻：等待 bridge ACTIVE 且 armed 后再启动。运行期不引入第二发布者、不改 checker 或验收条件。

## 前轮证据与下一步

#190 hover 和 ULog 通过；hover evaluator 10/11，失败项来自 pre-enable snapshot 四个控制话题均为 0 publisher。#191 的只读等待器确实在 ACTIVE/armed 后启动 graph capture，但 hover 仅 2.64 仿真秒即因 `px4_telemetry_stale` 自动降落，未采到 airborne graph；PX4 local-position/attitude source stamp 相对映射仿真时间分别超前约144/136ms，超过65ms既有future-age门。N05 14/14、ULog 12/12通过，最终 landed/disarmed；N07仍0/3。

下一项#192保持控制、runtime、N05与门限不变，只移除N07非必需的full-window freshness probe，继续运行必需truth/alignment/bridge/graph记录，确认该source-age门是否在较低只读订阅负载下仍触发。此假设未确认，不调整阈值。
