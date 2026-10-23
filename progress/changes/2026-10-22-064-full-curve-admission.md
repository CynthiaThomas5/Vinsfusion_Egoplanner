# #064 完整曲线准入与明确失败

持续任务见[对话摘要](../../collaboration/dialogues/2026-10-22-063-flight-safety-validation.md)。此阶段完成组件验证，未完成用户要求的完整仿真可飞。

EGO patch0039在0038后：规划占据谓词把unknown／outside阻塞；最终发布前、执行剩余曲线、完成后终点hold和紧急hold均作raw包络检查。导数B样条控制点的最大范数界定速度，每段中点球扩张vmax*dt/2覆盖连续间隙／末端；间隔位移≤resolution/4，最多10000段，资源不足拒绝。优化器旧局部检查仍可作候选生成启发，不能绕过全曲线准入。模型包络和误差／制动预算未完成标定，不能据此宣称已可飞。

NavigationCommand新增map_id并绑定当前目标证书；节点接受EGO planner_fault后中止活动任务，并清理仍可能提供最终hold点的已转发目标。map／定位／clock／shutdown失效也清已完成动作的hold。EGO规划失败或完整检查失败锁住自动重试，新目标必须重新准入。所有PX4输出仍由原桥独占。

内部全曲线查询读取序列化回调中的上一份完整融合，不要求下一张尚未融合的图像已完成；不读取pending图像，不改变0.4仿真秒实际融合／源龄和pose门。外部snapshot／目标球API维持原来的pending拒绝。假定仍用当前EGO默认串行callback group；以后改并发须加互斥保护。

验证：17包构建；在全部源码固定后强制重编plan_env／ego，184项回归＋真实ROS action集成通过。测试包含实际B样条导数范数界、弧线覆盖、末1/3、末端、间隙、非法输入及资源上限；action成功后hold故障也能取消。54文件fresh fetch一致。实际生产EGO进程＋合成深度夹具：0.5m球free792格，occupied4格、unknown792格／越界均正确；发布1条已知free曲线后注入新墙，full_curve_occupied停止，迟到曲线0；新阻塞目标planning_failed明确终止。组件没有PX4、Gazebo、VINS，不能替代真实仿真飞行证据。

原始日志artifacts/runs/flight-safety-20261022-064-{checks,component-01}，[结构化证据](../evidence/full-curve-20261022-064.json)。实际room仍缺完整机体已知free区域，起降自身／地面、误差和制动预算待解决；无起飞／飞行／阶段升级，继续总任务。

服务器续测补证（#067）：核对064-build-fusion-wait.log的17包构建、064-tests-fusion-wait.log的187项OK及真实action PASS；component-02/result.json为passed、after_completion=true，含wrong map、完成后hold障碍停止与planning_failed，故障后迟到曲线0。该轮查询包含大量no_fresh_fused_depth拒绝后才得到free，不掩盖或算作持续新鲜度通过。完整原始日志路径、component-02摘要及SHA256已补入结构化证据；历史184项/component-01记录保留。上述均为既有日志复核，不是本轮新构建或SITL飞行。065后续快照已发现局部0.5m free球，仍不能外推起降和全路径。
