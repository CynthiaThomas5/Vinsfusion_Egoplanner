# #062 在线目标球准入

对应[对话摘要](../../collaboration/dialogues/2026-10-22-062-online-goal-admission.md)，[验收范围与证据](../evidence/goal-admission-20261022-062.md)。未提交／推送，未解锁或飞行，未升级阶段。

- `uav_interfaces`新增`QueryOccupancySphere.srv`及生成注册；EGO patch0037在唯一plan_env上提供只读实际raw体素查询，与0021共享原有身份／融合新鲜度门。不改变原始建图／规划、求解器、健康阈值或PX4发布者。
- `sphere_query.h`使用球到格子AABB距离，包含相交格面，带1nm保守舍入余量；越界拒绝，未知不变free。上限半径2m／包围盒100000格，仅作资源约束。
- `uav_navigation/node.py`新增MapStatus及query客户端，工作线程异步等待、不占用EventsExecutor；转发前校验返回身份、中心／半径、计数及源戳，重查定位／地图上下文。超时、服务失联、unknown、occupied、越界等均拒绝；等待时取消不发布目标或无关轨迹清理；地图身份变化中止活动任务。配置新增0.25墙秒查询等待，其余半径0.5m／融合龄0.4仿真秒复用mapping配置。
- 新增纯证书校验`admission.py`；7项回归含编译运行生产C++查询、模型包络覆盖和错误返回验证。扩展真实ROS action集成：负分类、身份／源龄、超时迟到、地图变更、服务消失、并发、等待取消、活动任务map reset，并保留原clock／freshness／shutdown和250Hz负载检查。
- 新增只读`probe_goal_admission.py`；文档说明目标协议接受与实际转发区别，以及新版本不继承旧16m飞行资格。
- patch0037基于EGO锁定提交23a8d5a，0036之后应用；清单锁定补丁与三个最终文件哈希。53文件fresh fetch与实际vendor逐文件一致。

验证：`tools/project.sh build ros`最终17包退出0；`tools/project.sh test`182项＋ROS action集成通过，250Hz下最大pose接收龄0.053s。真实SITL `goal-admission-20261022-062-01`只执行只读探针：24次查询，13unknown、4outside_map、5no_fresh_fused_depth、各1map_id／epoch不符；10个VehicleStatus样本均DISARMED，导航目标转发0，容器退出0并关闭。无真实完整机体球free或occupied正例，不能据隔离测试算成live覆盖。第一次action断言大小写错误和本机无ROS模块的失败日志保留，修正断言后重测通过。

局限：仅终点球，未核验完整路径、地面／失效降落、不确定度或制动预算。真实wrong-frame查询先被融合门拒绝，未观察到frame_mismatch响应。旧默认16m目标可能因未知被拒绝；不以放宽unknown或门限恢复演示。VINS质量判据根因、真实回环与Nano仍待验证。下一步先做完整轨迹只读检查，不飞行。
