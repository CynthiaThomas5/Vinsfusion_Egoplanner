# #598 NavRL world选型（只读）

范围：[对话摘要](../../collaboration/dialogues/2026-10-30-598-navrl-world-review.md)。用户要求评估合适world与切换方式；仅新增选型证据/离线碰撞布局预览，运行源码、参数、当前GUI场景不变。

读取NavRL固定commit3725bcc2e7c1be4ecf1455d922299ae85042603a的world/launch/model元数据及许可。推荐floorplan2_static先接，floorplan4后续；floorplan2/4固定容器gz sdf -k均Valid/exit0，仅为解析证据，未运行场景渲染、VINS或导航。

产物：[选型报告](../evidence/navrl-worlds-review-20261030-598.md)、对应JSON源哈希、artifacts/runs/navrl-worlds-20261030-598-review中的离线平面图/边界。结构/格式检查不替代运行通过。

停止原因：本轮评估完成。未解：实际材质渲染、传感器、起终点/门宽/路径和SITL仍须在后续明确的接入任务中验证。当前世界未切换，无提交/推送。
