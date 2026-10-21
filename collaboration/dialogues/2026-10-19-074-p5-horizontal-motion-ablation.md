# 对话摘要：P5 #192 去爬升目标对照

- 用户目标：继续完成项目 `GOAL.md` 中的 P0–P6 单 D435i 仿真导航工作。
- 约束：不修改只读旧来源；真值只能作为只读评估输入；PX4 控制由 bridge 独占；不放宽门限伪造通过；本轮的失败诊断不能标成 P5 通过。
- 决定：基于 #191 固定环境运行独立 #192，只把目标垂直偏移0.15米改为0米，其余目标横向偏移、yaw、镜像、PX4/VINS 二进制、规划配置和健康门保持一致。
- 确认：#192 仍以 `normalized_cost=1.09435` 中止；越线时 truth-only 速度约0.023 m/s且无爬升，跟踪计数未降，唯一 cost 分组中 visual 占86.23%、IMU占0.10%。因此爬升不是这次重现的必要条件，但原因仍未定位。
- 确认：#192 ULog 重复 #191 落地后 local-position relaxed invalid → AUTO_LAND 到 DESCEND/failsafe 的路径；Offboard signal loss 在 AutoLand 后，电池 flags为零。
- 限制：cost 分组每进程仅保留首次越线样本，没有图像或逐特征残差；不能据此改门限。P5 继续进行中。
- 下一步：以同一镜像和门限运行 no-motion target/hold 对照，观察目标派发和无实际位移时质量门行为。
