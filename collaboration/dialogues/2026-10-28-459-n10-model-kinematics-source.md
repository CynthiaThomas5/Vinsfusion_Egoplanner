# #459：定位 N10 瞬时运动账本为空

- 用户持续授权完成 N10；故障注入与故障后校准按 #434 跳过，不能据此宣称 N15 通过。
- #458 已完成正常综合导航但总体为 `INSUFFICIENT`，安全正常落地并关闭。本次不改写其原始归档，也不补算为正式 N15/N16 次数。
- 查明记录为空的原因：PX4 的 `px4-rc.gzsim` 按 `PX4_GZ_MODELS/<MODEL_NAME>/model.sdf` 直接加载根模型；#458 的 observer 插件只写入 run-local wrapper，但 `PX4_GZ_MODELS` 仍指向源码模型目录。
- 当前子项只修复可选只读 observer 的根模型路径，记录路径/SHA 并做不发送目标、不解锁的 SITL 启动诊断。不改变碰撞几何、控制参数、拒飞逻辑、门限或故障测试范围。
- 待决：短启动诊断是否收到实际 Gazebo 状态；成功后，仍需后续完整正常运行采集全程物理步账本，才能评估连续净空。

## 结果

#459 observer 启动诊断通过：PX4 根模型实际指向 run-local overlay，SHA 与 manifest 一致且恰有一个 observer；Gazebo 话题 5.10 秒接收 854 条有效、单调状态，最大间隔 4 ms。独立读回保持 DISABLED/disarmed/landed/zero-control 后受控停止。PX4 native preflight 报告 false，但未请求起飞且项目没有新增拒绝条件。40 项定向测试、py_compile、shell 语法与 diff 检查通过。详细数据见 `progress/evidence/n10-model-kinematics-startup-result-20261028-459.md`。下一项 #460 重做正常完整路线以采集 physics-step ledger。
