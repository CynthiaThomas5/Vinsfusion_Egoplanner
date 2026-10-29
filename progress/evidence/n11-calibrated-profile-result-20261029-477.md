# #477 校准profile下的完整GUI预演

N11仍in_progress，正式0/3。本次按预声明profile从默认0.5/0.8恢复到#460既有0.4m/s、0.25m/s²配置；其它飞行阈值不改。实际pre-SITL记录在04:45:08 UTC生成，随后启动新容器，固定镜像ID/source-lock/profile哈希。启动后manifest精确核对参数，不倒填#476缺失声明。

12m动作、20sim秒保持、正常落地上锁及独立终态读回通过，容器exit0。桌面:11的Gazebo/RViz窗口证据归档。运动段10s平移RPE P95=0.03680281m≤0.05m，VIO各项通过；full-body sampled最小净空3.195182m、18915个airborne区间下界最小3.188820m，4ms物理状态完整、瞬时端点身份PASS；零违规接触。静态地图表面最大误差0.079556m≤0.1m，visible-free控制278264（跨快照计数），整格遮挡free为0。

唯一实测FAIL为队列趋势：acc/gyr current-before-feature-dequeue OLS slope=0.00243169245>冻结0；feature队列始终1，acc/gyr最大58，首尾四分段中位数都26。CPU15.064/32cores、内存4.483/66.882GB，无OOM或throttle，其余资源项通过。原判据和FAIL保留，未将准备协议改成正式通过。

已完成端到端N11适用层复算，输出FAIL/formal_count_eligible=false。额外修正了“不相关指标失败不应改变空场动态事件适用性”的离线判断，同时保留所有FAIL；25项测试通过。

[原始run](../../artifacts/runs/n11-20261029-477-calibrated-profile/)、[全复算](../../artifacts/reanalysis/n11-20261029-477-full-evaluation/n11-20261029-477-calibrated-profile/)。队列判据语义和决策见[#478](n11-queue-standard-review-20261029-478.md)。
