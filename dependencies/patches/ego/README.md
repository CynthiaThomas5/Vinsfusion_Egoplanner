# EGO补丁

来源：https://github.com/ZJU-FAST-Lab/ego-planner-swarm ，commit `23a8d5a191711dd65633df689bd00f55d4dea8f9`，GPL-3.0-only；只物化5个规划包。

有效顺序：0001–0011 → 0017 → 0018 → 0019 → 0021 → 0035 → 0036。具体应用根目录与strip见`dependencies/sources.json`；0036用binary模式保留原CRLF，重放不重写无关源码。

0035保留起始航向边界；0036对停止目标固定三次B样条末3控制点，约束终点、末速度和末加速度；非停止局部目标仍用原优化方式，碰撞／可行性检查保留。未纳入的unknown／扫掠／诊断候选不代表已解决，正式安全条款仍待验收。

补丁哈希、上游许可哈希、基准构建及当前验证范围分别记录在依赖清单和progress证据。
