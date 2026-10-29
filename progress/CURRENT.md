# 当前状态

更新时间：2026-10-30。执行模式：Goal完成；用户范围：完成N17、整理代码、上传既有GitHub、兼容设备可重建使用、结束当前单D435i仿真项目。

**当前范围完成，N17 passed，无下一必做子任务。** [最终验收](evidence/FINAL_ACCEPTANCE.md)、[里程碑](milestones.json)、[A–H检查表](goal-checklist.json)。N15/fault资格、实机、ARM和语义/信念/探索排除，不标通过；后续扩展需另行明确范围。

- #574四场景各3次、#575–#586共12/12当前控制版本冻结评估PASS；失败/中断/兼容别名原记录保留。
- #589从GitHub独立恢复所有来源/补丁/递归依赖，空build/install完成18ROS包6min44s和PX4 1141步；734单元与2套ROS集成PASS。实际GUI连续325.8sim秒、6段、71.502m、零违规接触、安全正常终态，独立驻留4.216–4.900秒，完整冻结评估PASS。
- #588原FAIL保留：返程驻留不足3秒；仅将连续任务native位置容差0.25收紧到0.10m后由#589通过，离线0.30m/15度/3秒标准未改。#587为postflight记录IO修复，不新增运行门。
- #590远端重建版本默认16m GUI及start.sh fly/status/stop PASS，正常落地上锁及独立safe-to-stop全部通过。当前无本项目飞行会话；未动其他容器。
- #573独立G调用与地图/RGB-D真实持久回读PASS。空Docker引擎镜像导入/ROS/Gazebo、GitHub环境LFS独立下载校验PASS。
- main源码已独立clone核对全部跟踪字节；发布标记sim-nav-v1.0.0，固定环境runtime-environment-v1身份见docker/environment.json。最终封装/远端tag核对日志在artifacts/runs/n17-20261029-569-audit；过程和实际限制见最终验收。
- 发布配置只清理两处说明文字及关联源哈希，JSON精确等价证明及8项回归通过，数值/控制字段不变。

迁移入口：README.md / docs/running.md。实际已验证Ubuntu24.04 x86_64+NVIDIA+固定Docker+X11；当前未接入第二物理设备，不宣称任意硬件可用或无限时长稳定。原始大数据留在artifacts，轻量证据/图表随源码。

早期CURRENT原字节保存在docs/history/current-before-n17-close-20261030.txt，仅作历史。恢复不需要任何活动飞行进程；若复跑，从新的run_id开始，不拼接旧epoch。
