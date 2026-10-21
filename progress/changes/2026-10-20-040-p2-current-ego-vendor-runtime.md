# 修改与验证记录

- 任务 ID／日期：P2 当前 EGO vendor 重建与动态运行复核 #280–#281／2026-10-20
- 对话摘要：[040 对话摘要](../../collaboration/dialogues/2026-10-20-040-p2-current-ego-vendor-runtime.md)
- 修改文件：新增#280/#281 artifact run reports、[#280定向构建证据](../evidence/p2-ego-current-vendor-build-20261020-280.json)和[#280–#281对比证据](../evidence/p2-ego-current-vendor-runtime-20261020-280-281.json)；补充#278/#279旧EGO二进制来源；更新前序地图证据、README、CURRENT、GOAL checklist和milestone引用。
- 行为与原因：核对#279使用的EGO二进制来自10月16日base install，且不含当前锁定源码patch 0010的同步诊断字段。用#279 fresh `uav_interfaces` overlay解决当前vendor源码缺失接口的问题，在#280全新目录构建固定EGO源码；#281再用该overlay跑相同动态无目标配置。无源码或阈值修改。
- 验证命令与结果：#280 `colcon --base-paths src/vendor/ego_planner --packages-up-to ego_planner ...`，固定Jazzy镜像下5/5通过；`strings`确认新`libplan_env.so`含patch 0010字段，旧binary无。#281 `bash -n`检查运行脚本，通过D435i动态run 35.015秒；MapStatus 153/153 ready，定位695/695 TRACKING，深度1338/1338 ready。Exporter将1193点快照写入PCD并逐点float32回读，metadata的run-report SHA与最终报告一致。
- 结果及限制：#279旧base EGO在约35秒窗口产生51条`odom or depth lost!`；#281 current-source EGO在同类run中0条，只有3条启动期`no odom`，随后进入WAIT_TARGET并干净退出。该版本化差异不证明timeout根因；#281无目标，不证明planner readiness、绕障、净空或PX4。记录运动区间有159次占据点数变化，但快照源stamp 33.644秒晚于运动驱动记录终点32.605秒；PCD仅含occupied。轨迹离线位置RMSE 9.31 mm；箱体／圆柱ROI各41/35点，P95表面残差3.44/11.64 cm，仍为探索性几何数据。GOAL C/F和整体A–H未通过。
- 下一步：基于当前SDF和机体包络挑选有可量化净空的走廊，先完成planner-only无PX4/无控制的绕障目标诊断，再补free/unknown、覆盖与正式阈值冻结。

本轮未提交或推送。
