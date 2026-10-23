# #062 在线目标球准入：实现与不解锁验证

**本小点完成，未通过轨迹／飞行验收。** 已在实际EGO栅格上新增只读球查询并接入目标转发之前。没有解锁、飞行、真值输入或新控制发布者，旧4m路线保持禁用。

## 行为

服务`/mapping/query_occupancy_sphere`绑定epoch／map_id／frame和原有0.4仿真秒实际融合／深度源门。检查与闭球相交的全部raw格子，格面接触计入；unknown／occupied不转free，地图边界拒绝。查询成功与球可用分开返回。没有复制整个栅格给导航，也不在膨胀层上重复加球半径。2m／100000格为资源上限。

导航使用canonical mapping的0.5m半径，回归确认覆盖当前0.48193587m标称全姿态包络；仍属PROVISIONAL，无标定不确定度或制动预算。要求地图当前有效、状态接收龄≤0.5墙秒；查询限0.25墙秒。action协议接受后才异步查询，失败结果为rejected，向EGO转发前再次检查上下文。地图身份改变取消活动目标；等待取消、并发或迟到回复不得转发，亦不清理无关轨迹。具体契约见[contracts](../../docs/contracts.md)。

## 验证与来源

- EGO锁定上游commit `23a8d5a191711dd65633df689bd00f55d4dea8f9`，GPL-3.0-only；0037追加在0036后。fresh fetch **53文件相同，差异0**，补丁和三个最终文件哈希已锁。
- `ssh gpu4090 'cd ~/D435i-VINS-EGO-ROS2 && bash tools/project.sh build ros'`：最终17包通过。首次构建2min1s；最终源码确认后增量构建7.20s。
- `bash tools/project.sh test`：最终**182项回归＋真实ROS action集成通过**。包含生产C++球／格相交与边界测试、返回校验、unknown／occupied／outside、map重置、服务失联、超时迟到、并发和等待取消；原epoch／clock回退／冻结clock／shutdown回归保留，250Hz负载最大pose接收龄**0.053s**。合成地图服务是隔离测试夹具，不能当作SITL实际栅格成功证据。
- 实际`sim goal-admission-20261022-062-01`后，仅运行`tools/probe_goal_admission.py --output /workspace/artifacts/runs/goal-admission-20261022-062-01/readonly-queries.json`，未调用mission／enable／arm。**24次查询**：13unknown、4outside_map、5no_fresh_fused_depth、1map_id_mismatch、1epoch_mismatch。最大墙钟往返**1.477ms**；10个车辆状态样本全部DISARMED（1），导航命令0。只读采样窗口之外不另作连续状态测量声明。会话已关闭，容器退出0。
- runtime contract：`9d1899af43e3168aa78843296472eed6e76bae5659fe0209017587b97a6f844f`；plan_env库SHA `73bcb58701cd08f9539dfa323eb1e7c7f7d0016f9453958277946356bd33cc3d`；VINS binary仍为`1f878b2dabe2610e7b56eb65db18df4cd6bebf26891827a7b15cb1c551a7dfba`。运行后才更新navigation README文案，因此完整source/config指纹不能直接继承到文案变更后的树；在线源码未再改。
- 本机无ROS环境，直接全unittest失败（ROS模块缺失）；容器全量通过。第一次action测试错把小写`rejected`断言为大写，已修正并保留失败日志；后续增加活动map reset／并发分支后最终全量通过。没有删失败或放宽健康阈值。

原始数据：`artifacts/runs/goal-admission-20261022-062-01/`；构建／测试／fetch日志与清单：`artifacts/runs/goal-admission-20261022-062-checks/`。机器可读摘要见[JSON](goal-admission-20261022-062.json)，本轮文件与对话见[改动记录](../changes/2026-10-22-062-online-goal-admission.md)。结构检查仅说明骨架一致，不替代上述运行证据。

## 限制与下一点

真实栅格未测到完整机体球free或occupied响应；生产C++和隔离ROS中的分支覆盖不能替代live正例。wrong-frame请求先遇融合门拒绝，未获得live frame_mismatch响应。远处unknown拒绝属于预期行为，不表示地图覆盖已经可靠，也不继承旧16m飞行资格。

终点球只反映查询时刻的局部地图；连接路径、全样条机体扫掠、失效降落／地面接触以及不确定度和制动仍待验收。下一小点先对完整轨迹做只读检查，不飞行。VINS先验累积／质量判据、telemetry_stale、真实回环修正和Nano迁移仍未解决，P4–P6保持进行中。

归档校验：`artifacts/runs/goal-admission-20261022-062-checks/SHA256SUMS`共22文件，清单SHA `cf597e193b0c7f50f4d1f1e8295ed818a575b79736a1825afeeb0357218711ec`。最终结构／Python编译／`git diff --check`通过，11个本轮代码／接口／锁定输入两机哈希一致。未提交／推送。
