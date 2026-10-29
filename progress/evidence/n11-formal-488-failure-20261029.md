# N11 正式运行 #488：FAIL（保留）

- Run：n11-20261029-488-formal04
- 冻结 runtime SHA-256：3a0111a1814c8f6ccb3f7155450fad044026201e8c94b844ce02210fffea5820
- 正式计数：不计入 3 次通过；#484、#485 的通过记录继续保留。
- GUI：Gazebo 和 RViz 在桌面 :11 可见；任务完成后 landed、disarmed、控制关闭，终态后控制为零，违规接触 0 次。
- 原始运行：[artifacts/runs/n11-20261029-488-formal04](../../artifacts/runs/n11-20261029-488-formal04)；只读重算：[n11-scene-acceptance.json](../../artifacts/reanalysis/n11-20261029-488-formal04-evaluation/n11-20261029-488-formal04/n11-scene-acceptance.json)。

## 未通过项

- 10 秒目标运动 RPE 平移 P95 为 **0.0630002 m**，冻结限值 **0.05 m**。
- 墙面几何为 **INSUFFICIENT**：15 张有效快照没有占据体素中心落在墙面支持半径 0.15 m 内；全程最近中心误差为 **0.1529 m**。地图分类仍 PASS。

到达、绝对定位误差／yaw、速度、地图源龄／更新龄、EGO 跟踪、机体净空、接触、资源／队列、身份与安全终态等其余适用指标均 PASS。地图源龄最大 0.160 s；native-work lag 最大 0.044 s，pending span 和 waiting features 均为 0。

## 判断

RPE 偏差集中在目标运动前 20 秒，后续 10 秒窗回到 0.05 m 以下；绝对位置误差升至约 0.19 m 后保持。前墙最近占据中心在最后快照距墙 0.1529 m，刚超出 0.15 m 支持带。两者与平移 VIO／地图漂移相容，但尚不能证明同因，也未定位代码缺陷。门限和 runtime 未修改。
