# P2 VINS Ceres/steady-clock 求解耗时对照 #287–#288

对应对话摘要：[2026-10-20-044](../../collaboration/dialogues/2026-10-20-044-p2-vins-monotonic-solve-diagnostic.md)。轻量证据：[p2-vins-monotonic-solve-diagnostic-20261020-287-288.json](../evidence/p2-vins-monotonic-solve-diagnostic-20261020-287-288.json)。两个运行的源码、构建、探针、clock采样与哈希见 `artifacts/runs/p2-vins-monotonic-solve-diagnostic-20261020-287/` 和 `...-288/`。

## 结果

- #287基于固定 VINS revision `72023bc5d2abb14faa4c02a5c040d84f996b587a` 和 canonical 0001–0005补丁，仅在run-local副本添加 `steady_clock` solve duration，保留Ceres `summary.total_time_in_seconds` 原字段。首次fresh build在安装时因遗漏上游 `../config` 失败；补齐同revision配置后，干净的`camera_models`+`vins`构建2/2通过，安装二进制SHA为`c06850ad9c1c3e40155af265427f2af9c542fa4acb52b28bb826566f10c0a739`。
- #287运行成功并得到39条B-spline，但首版probe保留字段白名单漏掉新增单调字段，因此该轮不用于耗时比较。保留其失败边界，#288修正run-local probe后复用同一二进制重跑。
- #288目标于5.009秒发送，ready MapStatus为902点，捕获41条spline。644条telemetry解析错误0；排除10条求解前默认值后，634条正的Ceres/steady-clock成对时长全部非负。Ceres值比外层steady-clock短17–66 μs，中位数短27 μs，绝对差P95约38.7 μs；本轮没有重现#284负值。
- #288主机时钟偏移监测覆盖81.51秒，偏移范围14.737 μs，最大相邻变化14.246 μs，未见明显回拨。定位另因`normalized_cost_exceeded`锁定（cost 1.000007；全轮最大1.06846）；EGO记录6条输入超时；每条都报告同步计数963、last sync stamp 36.532秒、最后occupancy更新36.648秒，随后有6条`Depth Lost! EMERGENCY_STOP`。同源时间窗内MapStatus仍ready，转发深度计数984→1014，优化里程计接收stamp 37.621–37.819秒；mapping adapter约4.29秒后才因normalized_cost关闭输入，因此后续定位锁/清图未触发这组超时。故障位于自维护适配器输出之后、EGO同步输入更新之前；DDS reader与EGO callback/executor未区分。另有1507条终点位于障碍内警告、13条“suddenly discovered obstacles”消息，均为无控制器的内部规划日志。
- 运行图无控制节点或控制话题，无运行时真值订阅、PX4、轨迹服务器、控制器或轨迹执行。

## 修改与验证

- 只新增`artifacts/runs`内的第三方源码副本、run-local诊断patch、构建与运行产物，以及进度/证据文件；`src/vendor/vins_fusion`、依赖标准patch链、定位健康逻辑和健康阈值均未修改。
- #287 `camera_models`与`vins`干净重建2/2通过；安装包路径解析及二进制字符串检查通过。#288使用同一二进制；采集644条telemetry、零解析错误，离线SE(3)轨迹评估完成。两个报告所列原始文件哈希复核通过。
- `python3 tools/project_status.py`：PASS（Structure/design check）；`git diff --check`、`git diff --cached --check`及#286–#288原始采集哈希复核：PASS。结构检查不代表SITL或飞行验收。

## 状态与下一步

#284负时长在#286/#288未复现；当前对照显示Ceres与steady-clock耗时紧密一致，尚不能追溯确认#284成因。保持fail-closed健康门、`max_solve_s=0.1`与`max_normalized_cost=1.0`不变，健康阈值仍为PROVISIONAL。下一步继续独立诊断EGO输入同步问题，并补地图free/unknown、覆盖与持续证据，推进正式D/E/F验收。P2阶段表仍passed；P4/P5/P6和GOAL A–H整体仍未完成。
