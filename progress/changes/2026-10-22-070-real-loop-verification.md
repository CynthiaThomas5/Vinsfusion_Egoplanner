# #070 第2个小目标：真实回环验证

[授权与范围](../../collaboration/dialogues/2026-10-22-070-real-loop-verification.md)。本轮仅验证实际回环与图优化，不宣称消漂效果，不接导航／PX4控制。

文件和行为：preflight_scan.json新增loop_revisit_profile，复用069同一位移／yaw路径重复7次，总742仿真秒，上限1500墙秒；原drift、smoke、coverage配置不变。probe_preflight_scan增加新profile及对应执行期限，健康／身份／DISARMED要求不变。record_fixture_truth增加有界max-wall-s参数，默认650秒不变；record_loop增加结束marker和最长时间参数，原flight.json／380秒／2秒尾段默认保持，新增只读status JSONL便于观察关键帧／候选／验证／优化次数。

新增debug_truth/evaluate_fixture_loop.py及几何回归：从实际后端graph读取回环两端、源时间和PnP相对约束，以Gazebo模型源戳及单一SDF外参计算独立相对位姿误差，不拟合轨迹。检查实际候选、验证、优化、有限图与非零位姿更新，以及独立namespace、无truth／控制输入输出、队列界和曝光配对。沿用059诊断界限0.25m／5°，不修改任何在线门限。

运行前198项回归9.025秒＋真实ROS action集成通过；安装VINS／loop_fusion、健康／回环配置及src/own保护哈希保留在070-checks。没有修改安装ROS／第三方算法，不重编。路线审查复用069几何路径并验证新增所有目标均在原集合内，只增加重复次数。

最终结果见下文；关键帧图或候选计数本身不作为验证回环／消漂通过。后续目标须用户另行审阅。

01试次保留失败：原0.2m观察器在3轮后仅17帧；45墙秒只读采样收到7个原始关键帧，相邻位移0.1275–0.1570m，被观察器间距筛选减半。第4轮又先于计划中止操作自然触发normalized_cost_exceeded（q=1.41019），运动停止，728状态样本均DISARMED，fixture仍attached。最终记录21关键帧、候选／验证／优化均0。计划SIGINT未发出（定位probe已自然退出），intentional-interruption.json明确注明实际失败，不覆盖原始result。

另有本轮操作失误：旧loop_runtime.sh尚在等待C++进程时更新了文件，随后旧shell按变化后的偏移继续读取时报unexpected EOF，wrapper退出2且未留下后端exit-code；不能推断C++正常退出。日志保留，本轮checker把缺失退出码记None／失败，不补造成功。确认live DISARMED后01容器停止。02启动前检查shell语法并冻结全部启动脚本，运行期间不修改。

02仅将观察器取样改用显式config/components/localization/loop_observer_local_revisit.json（0.1m），默认0.2m文件原样保留，BoW／PnP／健康门和binary不变。run_loop_observer及标准loop入口允许选择config目录内的JSON，manifest记录路径及哈希；新增默认不变／显式选择／路径越界拒绝测试。199项8.631秒＋ROS action通过后才在新epoch启动。02仍只验证第2个小目标，后续误差改善不在本轮范围。

最终02通过第2个小目标：94关键帧、43候选、2条验证回环、2次优化，13项独立检查全部通过。7→74／0→80两条约束分别跨502.656／602.184仿真秒，独立平移误差3.15／2.65cm、姿态误差0.199／0.224°；最大图位置更新8.35cm仅说明非零更新，不代表误差改善。完整742秒配置、47段运动完成，1484状态样本均DISARMED，定位末态valid；脱离／移除确认、实际模型无支架，后端及包装退出0，项目容器已停止。无关容器保留。

验证：最终 `bash tools/project.sh test` 199项8.905秒通过，真实ROS action集成通过（250Hz时钟下最大pose receipt age 0.053秒）；`python3 tools/project_status.py` 通过，仅为结构检查；`git diff --check` 通过。日志和哈希见 [证据JSON](../evidence/real-loop-20261022-070.json)，方法、失败试次及限制见 [报告](../evidence/real-loop-20261022-070.md)。02冻结输入及运行前后指纹一致，原有保护文件哈希不变；未改数值算法，无需重编。未提交／推送，不升级正式里程碑。

局限：单场景未武装支架试验，01／02不是严格稳定性A/B；仍未量化回环对漂移的改善。下一小目标建议仅用02已存数据、共同起始对齐比较原始／修正位置和yaw误差，待用户批准，不在本轮实施。
