# GOAL C EGO unknown-space处理试验 #289

## 用户约束与决定

- 继续按根目录 `GOAL.md` 推进单 D435i P0–P6；不改旧PX4/ROS来源，不混入vendor工作树已有修改。
- 避免EGO把未观测区域当作自由空间；先在隔离源码副本试验，不改canonical依赖链、阈值或控制发布者。

## 已确认结果

- `GridMap::isUnknown`在基线中存在，但`getInflateOccupancy`只返回膨胀位，unknown初值的膨胀位为0；EGO planner boolean collision checks把unknown当成free。
- 候选patch `0020-unknown-as-obstacle-experiment.patch`基于固定EGO revision、在0001–0011及0017–0019之后应用；SHA-256为`1041f74fd2b8c0409f348f272d7e48f0d7a62d9552e31a741b9296aa8ffdb0b8`。只改run-local副本。
- #289 fresh 5包构建通过，planner在ready地图派发目标并输出91条B-spline；但出现82条输入超时、2747条终点障碍警告，末段同步pose被判为超出map范围。没有控制或轨迹执行。
- 前两段同步计数停滞时，上游MapStatus和里程计仍继续；后段同步计数增加但`last_sync_in_map=false`。当前读端传递与地图边界问题仍未解决。

## 待办

- 保留候选patch作诊断，暂不加入sources.json或canonical vendor。
- 用低负载同钟trace区分DDS reader、EGO回调/message-filter与局部map边界；提供free/unknown计数和几何快照后再评估正式导航。
