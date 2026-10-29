# #498 N12 正式02：RPE FAIL保留

独立可见GUI冷启动正常完成单柱绕障、目标、native请求5sim秒驻留、20sim秒保持、降落/上锁；独立安全读回全部通过后停止。N12累计0/3，正式2次均FAIL；#496是goal/enable前启动失败，不计正式飞行。

驻留调整经实测确认：独立位置/yaw连续窗口4.248sim秒≥3秒。单柱证明PASS，实际/参考穿越平面侧方y=-1.790161/-1.848813m，3张穿越前同身份raw/inflated快照支持；柱体侧面误差0.087056m。完整机体无接触区间净空下界0.551996m≥0.1m，零违规接触。地图、跟踪、绝对/速度误差、资源/原生队列和记录完整性通过。

唯一真实失败为goal-motion RPE10平移P95=0.059407m>0.05m；旋转P95=0.173525°及保持RPE通过。高误差窗起点集中10–20秒，分段P95=0.062896m。源码/配置/门限未改，不能把action或绕障成功算完整通过。

[完整合同](../../artifacts/reanalysis/n12-20261029-498-formal02-evaluation/n12-20261029-498-formal02/n12-scene-acceptance.json)、[单障碍证明](../../artifacts/reanalysis/n12-20261029-498-formal02-evaluation/n12-20261029-498-formal02/n12-obstacle-route-evaluation.json)、[RPE时段分析](../../artifacts/n12-prepared/n12-20261029-499-fixed-input/498-review.json)。下一#499复用MCAP进行完整原生输入回放与估计器机制诊断，不继续盲目飞行。
