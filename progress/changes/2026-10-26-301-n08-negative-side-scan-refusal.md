# #301 N08 负 Y 侧视尝试被定位健康门中止

## 结果

既有 `n08_overhead_negative_side_view` 新冷启动路线在 7/16 阶段时以 `normalized_cost_exceeded`=1.058738 停止，超过原 1.0 门。未到 yaw−π/2 侧视阶段，未生成 post-release N05 准入或 flight。fixture detach/remove 与模型 absent 已确认；PX4 landed/disarmed、bridge DISABLED，独立控制 topic 为0，项目容器安全停止 exit0。

详见[#301 evidence](../evidence/n08-negative-side-scan-localization-refusal-20261026-301.md)和同 run 原始文件。

## 下一步

#302 在 #300 已通过的 overhead/positive-side 路径上增加一次起点附近的负 Y 侧视与回中，避免 #301 未到目标阶段的长回程；所有准入和制动门不变。
