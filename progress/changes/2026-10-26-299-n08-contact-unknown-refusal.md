# #299 N08 接触面 raw unknown 前置拒绝

## 任务与边界

沿既定 N08 方案在新冷启动尝试高窗口 motion-cancel。只进行 N05 未武装全机支架扫描与 fresh map 准入；不绕过 unknown 拒绝，不进入飞行。

## 结果

支架路线状态日志到达 6/6 阶段并移除夹具，但 fixture helper 报逐条命令的 fresh DISARMED 状态错误，故扫描不作为完整通过。释放后的同身份 raw-map fresh N05 检查因接触平面 24 个 unknown 格拒绝；online/offline 一致。HOLD unknown=0，ground plane 有效且 z=−0.35 m，因此这些格不符合地下排除条件。没有 goal、enable、控制或 flight。独立读回确认 DISABLED、disarmed、landed、控制输出 0，项目容器停止 exit 0。

## 记录与下一步

- 证据：[N08 #299 报告](../evidence/n08-n05-contact-unknown-refusal-20261026-299.md) 和 JSON。
- 原始产物：`artifacts/runs/n08-cancel-highspeed-prescan-20261026-299/`。
- #300 仅把 N05 scan profile 切换为已有 `n08_overhead_free_sector_view`，以俯视／侧向视角观察接触面；地图、门限、N08 试验配置不变。通过新的 fresh N05 前不启动 mission。
