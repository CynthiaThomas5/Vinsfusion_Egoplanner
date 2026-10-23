# #069 重复返回里程计漂移基线

[对话摘要与授权](../../collaboration/dialogues/2026-10-22-069-repeat-return-baseline.md)。本轮只做用户批准的第1个小目标：连续至少5分钟、至少3次实际同位置／同朝向返回，测量原始VINS漂移。没有实施后续回环或控制接入。

修改范围：

- config/components/simulation/preflight_scan.json：追加独立drift_profile，保留原smoke／coverage。先静止3秒、提升12秒、参考停留10秒，再执行3个100秒周期（1.2m外移、小角度0.3rad转出／转回、返回、停留30秒），最后下降与静止，总342秒。drift_measurement提前声明最后5秒统计窗口、3返回、300秒间隔和实际重复姿态容差2cm／1°；容差衡量实验重复性，不是里程计健康或精度门。
- tools/probe_preflight_scan.py：允许drift，校验静止参考／返回配置，记录stage/label/cycle及源clock区间，保存完整阶段与墙钟时长。仍逐步要求新鲜DISARMED、同epoch健康；没有ROS目标／控制或真值订阅。
- tools/debug_truth/evaluate_fixture_odometry.py：输出固定起始对齐后的误差向量与独立真值坐标／yaw，保留源戳、原插值边界和尺度1。不对每次返回重对齐。
- tools/debug_truth/evaluate_return_drift.py及测试：按已冻结protocol与已完成阶段取停留尾部5秒，先验证源时间覆盖和实际真值重复性，再比较每次返回误差及相对参考增量。趋势仅描述本轮4个停留点，不作长期保证。

执行前保留本轮相关文件快照、VINS/健康配置/src/own/dependencies哈希；在artifacts/runs/odometry-drift-20261022-069-checks保存protocol、几何审查、验证和原始结果。名义支架路径对非地面障碍的保守球余量约1.558m；地面／支架接触是本实验有意接触，不是自由飞行安全证书。生产ROS源、VINS binary和健康门未改，因此未重新编译ROS；196项Python/C++探针回归与真实ROS action集成通过后才启动实验。

结果：第1个小目标的测量完成；344.388仿真秒、参考至第3次返回301.116秒，3个实际返回有效。新增位置漂移1.85→3.73→5.72cm、航向0.248→0.424→0.655°，表明本场景存在累积漂移，不能声称“不漂移”。全过程位置RMSE3.61cm／最大7.40cm，yaw RMSE0.416°／最大0.733°。这是局部1.2m支架往返、单次冷启动，不是自由飞行或长期稳健性证明。

运行23段完成、outcome=unarmed_support_drift_completed，墙钟433.034秒；689状态均DISARMED，脱离／移除确认成功，实际模型列表无支架，停止前再次确认DISARMED后stop退出0。保护输入、本轮冻结输入及运行fingerprint一致；其他容器未动。完整[测量方法、命令与局限](../evidence/odometry-drift-20261022-069.md)，[机器证据和SHA256](../evidence/odometry-drift-20261022-069.json)。

196项回归8.860秒＋ROS action集成通过，250Hz最大pose接收龄0.053秒；结构和diff检查记录在069-checks。本轮无生产ROS源码或binary修改，故未重编，不能继承旧飞行资格。P0–P6／S1–S6状态不变。到此停止第1目标，待用户审阅下一小目标，不继续回环或算法修复。
