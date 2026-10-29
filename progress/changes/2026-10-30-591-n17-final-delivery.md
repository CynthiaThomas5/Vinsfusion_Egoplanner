# #591 N17与当前仿真范围收尾

本轮ID/目标：N17-20261029-569至N17-20261030-591，Goal完成模式；完成用户授权的代码整理/GitHub/可迁移使用/当前项目收尾，N15与实机排除。对话摘要：[执行摘要](../../collaboration/dialogues/2026-10-30-588-n17-final-delivery.md)。

实际改动：修复固定镜像内容身份/导出；正常入口补独立qualification与安全终态记录、GUI额外只读订阅者兼容；默认16m使用-8m起点及已验证低速参数；校准VINS0022来源固定；postflight原子JSON/只读解析；四场景固定SDF/冻结评估与输入；连续任务native精度0.10m；重写当前运行/架构/契约/README，保留历史；原有7包Apache-2.0声明保留，第三方分别保留；发布说明文字精确等价验证；最终A–H/P/S/N状态回收。无新增健康门/CPU或记录器降落分支。大数据、下载依赖、构建、凭据不进入Git。

验证命令/结果：

- 全新GitHub clone；bash tools/project.sh fetch；bash tools/project.sh build all：18ROS包6min44s、PX4 1141步，退出0。
- bash tools/project.sh test：734单测、两套ROS集成PASS；最终说明文字/源哈希联动后8项目标配置/机体几何回归PASS。
- 冻结矩阵#575–#586：四场景各3，12/12 PASS；#589连续GUI325.8sim秒、6段、零违规接触、完整离线PASS；#590真实start.sh fly/status/stop与独立normal qualification PASS。
- 独立空Docker引擎load及ROS/Gazebo运行PASS；GitHub固定环境LFS独立clone/download SHA PASS；最终main591a8a79f6f1e898239c854eeb2f27144c368940独立clone及全部跟踪字节PASS。源码/环境上传已获用户明确授权，采用命令级SSH443，无改可见性/SSH配置。
- python3 tools/project_status.py、git diff --check通过。正式/失败/中断记录及精确原始/派生身份保留。

产物：[最终验收](../evidence/FINAL_ACCEPTANCE.md)、[发布证明](../evidence/n17-github-publication-20261030-591.json)、[运行冻结](../evidence/n17-final-runtime-20261030-590.json)、[证据索引](../evidence/n17-delivery-evidence-index.json)、docker/environment.json；构建/发布/封装日志artifacts/runs/n17-20261029-569-audit，完整导出artifacts/exports/n17-20261030-final。

未解项/限制：无当前范围未完成必做项。物理第二设备未接入、故障/实机/ARM/无限时长稳定性均不声明；五分钟资源与内存增长、观测时序局限如实报告。#588驻留失败等原失败未覆盖/抹除。未新增正式故障测试次数。

停止原因：完成当前用户授权范围。下一步：无必做队列；用户可按README在兼容设备部署或明确另开扩展范围。最终main/tag与包SHA256SUMS核对在发布日志中记录；不把校验本身称为SITL。
