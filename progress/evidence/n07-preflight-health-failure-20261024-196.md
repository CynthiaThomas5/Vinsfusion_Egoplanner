# N07 #196：支架扫描期间 VINS 健康门失败

## 结果

**FAIL_NO_FLIGHT；N07 连续通过计数从 2/3 重置为 0/3。** Run 目录：`artifacts/runs/n07-20261024-196-01/`。本次未开始 N07 飞行验收。

## 固定条件与 N05 准入

运行使用固定镜像 `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`、runtime 配置 SHA-256 `1ddd6838ae2a678f89547ce90eea849582edcc29cddab341667bd2d1d9d3e360`、runtime-contract 文件 SHA-256 `856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb`、spawn `-6.5,0,0.3,0,0,0`、`wall_box_column` 布局和支架路径 `n06_full_airframe_retreat_240_oblique_separated_return`。健康、控制及准入阈值均未改变。

初始 N05 online/offline 检查一致按 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope` fail-closed。未武装支架扫描在 **7/12 阶段**时，VINS 报 `normalized_cost_exceeded`，normalized cost `1.0601070975543245`，状态 `state=4, valid=false`；helper 以 `localization changed or became invalid during physical scan` 退出，`n05-fixture.exitcode=1`。N05 在线窗口、ready marker、释放后/current-area 检查和 14 项摘要均未完成。

初始门拒绝的是飞行器包络中的 raw unknown；本次扫描和任何飞行均没有把地下空间当作可飞区域。

## 飞行与安全收尾

`n05-prescan-ready.json`、`n05-run-summary.json`、`flight.json`、ULog、独立 evaluator 和 ROS graph 飞行报告均未生成，因此没有解锁、目标或起飞命令，也没有空中证据。

helper 记录支架状态 `attached → detached`，移除服务确认成功且 Gazebo model list 中没有 fixture；安全 cleanup 确认 landed。第一次 bridge ROS 读回发生在 DDS 发现 bridge status publisher 前，未能解析主题；等待发现后重读，得到 `phase=DISABLED`、`control_enabled=false`、`armed=false`、`landed=true`。PX4 读回为 `arming_state=1`，LandDetected 为 `landed=true`。随后 `bash tools/project.sh stop n07-20261024-196-01` 退出 0，容器 `Exited (0)`，无活动项目容器。

## 下一步

本次 VINS 健康失败使连续计数重置，不能抵扣 N07 的 3 次独立冷启动。#197 使用同一固定镜像、配置、spawn、布局、支架路径及既有验收门继续一次全新的 cold start；不抬门限、不改源码或配置。N05 全部准入检查通过前不启动飞行。地下空间不作为飞行目标或飞行体积。

逐文件哈希见[JSON 报告](n07-preflight-health-failure-20261024-196.json)。
