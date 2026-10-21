# GOAL C 密集曲线校验后的同刻快照 #319

使用 #318 的 patch 0029 Release binary，在独立 D435i/VINS epoch 中复测同 planner 配置，并在每条 spline 到达后请求只读 occupancy snapshot。探针收到两个不同 trajectory ID；第一份服务请求因无新鲜 fused depth被拒，第二份 ID 2 快照成功，header stamp 与 spline start_time 完全一致，深度源龄66 ms。

ID 2 的 414 个 10 ms中心线样本全部位于地图内且均为known-free，raw occupied为0、inflation-mask命中为0；距occupied voxel box的最近离散样点约0.628 m，比既有0.482 m名义球半径高约0.146 m。地图known约0.62%，因此这只证明该次中心线与已知栅格mask的对照。无controller、trajectory server、PX4、truth或control topic，样条未执行。

决定：patch 0029 留在 experimental patch 栈。#318 live log 中的3次候选拒绝和本次单条通过路径的快照对照支持继续小范围重复，但不支持canonical接纳或GOAL C/D/F验收；下一步应在独立epoch/布局复测，并补地图覆盖、扫掠包络及跟踪误差证据。
