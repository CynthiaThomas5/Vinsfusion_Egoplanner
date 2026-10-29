# #293：按EGO样条终点与PX4实测停止确认取消hold

## 目标

修复#292中motion-cancel runner永久等待`PositionCommand.COMPLETED`的问题，并修正离线取消结果字段的验收错误。

## 证据与修改

#292 caller-cancel三字段正确；EGO生成新traj_id=2停止样条，16个raw-map查询free，速度上界0.08712 m/s、reference tube均通过。真值测得cancel-stop行程0.29850 m，PX4实测低速保持约9.2仿真秒。native runner却因flag始终READY等待超时并operator-disable。源代码确认`traj_server`在样条终点发布零导数终端位置，但每次仍标READY，故等待COMPLETED不可能通过。

runner现在根据EGO knot有效域和B-spline start_time计算终点，再核对同轨迹稳定的末端位置/零导数命令与PX4实测速度门3秒hold；保留ACTIVE、解锁、定位和telemetry检查。停止时间等待由预飞测得RTF与样条duration推导。N08 evaluator现在分别核验action status、outcome、reason，不再混淆`canceled`和`caller_cancel`。

## 验证与限制

- `bash tools/project.sh test`：354项通过，navigation-adapter integration通过。
- `tools/ros_tests/test_n08_trial_snapshot.py`：8项通过。
- #292独立部分曲线表明低速hold实际发生，但native验收因错误状态事件超时，最终landing candidate/command没有执行，故#292保留FAIL。
- 修改仅为运行期Python与离线evaluator，依赖下一次run的runtime manifest认证；EGO二进制未改变。

## 下一步

新冷启动#293，通过N05扫描、只读preflight及任务前current-area gate后执行`single_goal motion_cancel 0.04 0.06`。要求停止样条达到source-clock终点、实测静止保持3仿真秒、通过终点raw-map landing admission并完成PX4 landed/disarmed；随后评估独立制动曲线。
