# N17默认交付入口与接口验证 #573

Goal范围为完成N17、整理代码/GitHub上传/迁移可用。#570干净构建18包/PX4后，#573实际Gazebo/RViz GUI启动，默认16m目标真实飞行PASS，独立0.3m/15度/3秒到达、零违规接触、唯一控制发布者、正常落地上锁/控制归零及独立safe-to-stop全部PASS。普通navigation生成qualification.json，start.sh status/stop真实使用通过。归档artifacts/runs/n17-20261029-573-default-demo及-stack。

独立tools/probe_handoff_interfaces.py在正常落地后实际提交当前观察位姿，action接受后以map_query_occupied明确失败；按G“到达或失败结果”条款有效。地图状态查询、旧epoch拒绝、带位姿RGB-D和定位/epoch接口全部有效；调用程序自身PX4控制发布topic为空。

通过MCAP保存10组真实RGB-D和MapStatus。tools/inspect_handoff_archive.py实际反序列化，图像完整字节/CameraInfo K/源时间位姿/epoch/map_id/标定与输入配置一致，未向ROS重放或发布控制。GetOccupancySnapshot实际保存并回读raw/inflated npz及metadata，同epoch/map_id与关键帧一致。未将地面观察位姿拒绝说成G导航到达或新增飞行。

此前#571写死2订阅者的图检查在GUI/readonly4订阅时拒绝，未起飞；已改为唯一supervisor publisher及必需planner/bridge端点。#572在修复复制前误启动，未飞即关闭；两次都独立确认DISABLED/landed/disarmed/control disabled后安全停止归档，不计正式次数。12项定向测试通过，旧日志保留。

产物artifacts/runs/n17-20261029-573-completion/audit.json含源/运行身份及关键输入SHA。默认示例/G/地图关键帧回读子项完成，但当前交付版本四场景三次冷启动回归、最终A–H和发布/异机仍待完成，N17 in_progress。源码主分支尚未提交推送；固定环境LFS上传进程仍实际存活。停止原因：本子项完成且本运行已安全停止；Goal继续下一子项。

对话collaboration/dialogues/2026-10-29-569-n17-delivery.md
