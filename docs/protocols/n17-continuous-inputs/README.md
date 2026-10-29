# N17最终连续任务的固定实验输入

#589在GitHub源码独立恢复/重建目录执行，同一会话325.8sim秒、6段独立到达。配置为config/components/navigation/n16_continuous_goal.json，离线标准config/acceptance_n16.json，协议docs/protocols/n16-continuous-load.json。原#588失败协议保留于docs/history/n16-continuous-load-release588.json。

run.sh和record_context.py是本次实际使用脚本的字节归档，不替代日常start.sh入口。运行前使用qualification/corridor.sdf作为该次活动世界、协议指定planner配置和delivery-inputs/spawn.json，GUI/contacts/kinematics/sensor capture开启，stack-started后启动只读context/static-map/process观察器，再在容器/workspace执行run.sh RUN_ID config/components/navigation/n16_continuous_goal.json navigation。context第三参数为/workspace/docs/protocols/n16-continuous-load.json。独立safe-to-stop全部通过后再停止本次容器。

不同设备重新构建会产生新的二进制/运行身份，须在新运行前冻结本机运行契约并生成新协议，不把本次旧协议哈希当作异机二进制身份。原始记录只作输入，prepare_n16_evaluation.py --output-root生成独立派生视图。evaluate_diagnostics.py接受派生视图与新输出目录，给出地图/时序/RTF曲线，不增加数值验收门。

默认迁移示例使用仓库默认世界和start.sh，不需要上述专项输入或任何旧artifacts。
