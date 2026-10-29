# N08 #303 侧视后恢复窗口

- #302 到达负 Y 侧视并回中，但开始 z=1→0.5m 支架下降时 normalized_cost 达1.025847，越过原1.0健康门；没有 post-release N05。
- #303 使用新 profile `n08_overhead_free_sector_with_negative_side_recovery`，唯一增量是回中 yaw0、z=1m 后增加15s neutral hold，再运行原回收下降。
- 所有 N05/N08阈值、unknown判据、速度、goal和制动配置不变。静态37项profile测试、JSON/shell/project_status/diff检查通过。
- 待验证：新冷启动完整 scan 和 N05 release/current-area gate；N08 corridor全free前不启动mission。
