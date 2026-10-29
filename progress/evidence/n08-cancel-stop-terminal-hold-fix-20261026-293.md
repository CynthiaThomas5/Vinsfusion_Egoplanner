# N08 #293：以B-spline终点与实测静止hold判定取消停止

## 修复

当前EGO `traj_server` 在B-spline有效时间结束后保持终点位置并发布零速度/加速度，但`PositionCommand`的flag仍为READY。runner不再等待不会出现的COMPLETED事件。

motion-cancel验收现根据`Bspline` knot domain及绝对`start_time`计算source-clock终点；需要同一goal/epoch/trajectory在终点后至少两条相隔50 ms的稳定末端命令，末端参考速度和加速度均为零。随后使用新鲜、source-time单调的PX4 local-position样本，要求水平速度<=0.03 m/s、垂直绝对速度<=0.05 m/s，持续既有3仿真秒hold；期间bridge必须ACTIVE/armed且健康新鲜。wall上限由样条时长、hold和本run只读preflight RTF推导。没有改变制动速度、地图、tracking、健康或landing阈值。

新增测试覆盖B-spline有效时间域、READY终端保持、终点/零导数条件、PX4速度门，以及运行时evaluator对cancel action字段的manifest认证。独立evaluator修正为核对status=5、outcome=`canceled`、reason=`caller_cancel`、success=false各自正确值。

## 验证

- `bash tools/project.sh test`：354项通过，包含navigation-adapter integration。
- ROS snapshot admission：8项通过。
- 运行期Python及evaluator更改由下一次`runtime-contract.json`逐字节锁定；没有编译型源码变化，未重编EGO二进制。

修复后的冷启动、motion-cancel、完整停止hold、destination landing与独立N08验收仍待#293实测；N08没有通过。
