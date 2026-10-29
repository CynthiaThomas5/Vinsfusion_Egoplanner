# N08 #302 负侧视观察 profile

- 背景：#300 的 motion gate 在同一 raw map 中对负 Y 薄层 unknown 拒绝，#301 长扫描在到达负侧视角前因原 normalized-cost 门停止。
- 决定：以 #300 已完成且 post-release N05 通过的全路线为基线，只在回到起点后加入 yaw−π/2/pitch0 侧视和 yaw 回中；保持原有双向 N05 覆盖路径和全部阈值。
- 修改：新增 config profile、Python/shell allowlists、针对 profile 顺序和基线不变的回归检查。
- 静态验证：36 个 profile tests、JSON、shell syntax、project_status 及 diff check 全通过。
- 待做：SITL fresh scan、post-release/current-area admission 和 N08 corridor；通过前不飞。
