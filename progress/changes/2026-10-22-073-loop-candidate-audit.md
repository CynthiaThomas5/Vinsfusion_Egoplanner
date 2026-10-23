# #073 第5个小目标：定位回环候选通过率差异

[用户授权与边界](../../collaboration/dialogues/2026-10-22-073-loop-candidate-audit.md)。只读检查070-02与072原始观察记录、运行manifest及现有VINS补丁；未启动仿真，未改自维护／第三方源码、配置、阈值、控制链路或运行数据。

## 发现

两轮均有94个关键帧、43次loop-candidate计数；计数事件都发生在KF51–KF93。现有补丁`0015-loop-observer-transport.patch`在检测到`loop_index != -1`时递增`loop_candidates`，随后调用`cur_kf->findConnection(old_kf)`；只有调用返回true才递增`verified_loops`。因此070-02的2条通过边与072的1条通过边，在计数层明确差于候选提出后的几何连接验证门：070-02接受当前KF74→旧KF7、KF80→旧KF0；072接受KF57→旧KF0。分别有41/43、42/43次候选没有通过该调用。

两轮runtime合同SHA相同（`6a5ce037e496ecd58fd298440462257a5650fa0ff021bd883085e42c8b370cdb`），VINS loop observer executable、配置摘要、资源、限制和session settings摘要相同；生成的epoch专属session文件哈希集合不同。规范化后的47阶段标签／目标序列相同。两轮均94关键帧、43候选，`same_camera_exposure`与`bounded_queues`检查通过，最大image/pose间隔1ns、`dropped_sync=0`。这些记录没有显示候选数或传输配对数量导致差异。

070-02的验证边分别在cycle 6 inbound（KF74）和cycle 7 outbound（KF80）；072仅在cycle 5 inbound（KF57）验证成功，成功位置不在同一轮次。后端记录未保存拒绝候选的旧帧索引、BRIEF匹配数、PnP/RANSAC内点、重投影误差或失败原因。记录中的关键帧点云数量不是描述子匹配／PnP内点，不能用它们代替缺失的几何诊断。故本次**精确定位到候选后的`findConnection()`接受门，但不能确认内部失败子条件或根因**。

## 核验与下一步

机器证据复核了观察记录、状态流、stage trace、两个run evaluator和补丁文件SHA-256；两个evaluator各自的13项回环子检查均为true。解析器重算了候选事件关键帧索引、验证计数转变和阶段标签。没有构建或软件回归：本轮不含代码变更，只读分析。正式里程碑不升级。

下一目标建议增加逐候选只读统计（BRIEF匹配数量、PnP/RANSAC内点与明确失败阶段），保证计数不参与决策，再在同一支架路线fresh epoch复测。它需要新增第三方补丁、重建并重新采集；须用户批准后实施。
