# N08 #309：N05 支架扫描健康拒绝

- 用户目标：按已讨论的单程目标／显式另行返航规则完成 N08；普通目标到点后停止，不自动返航。
- 范围：Goal 完成模式，继续 N08 必要子项；不复测已通过的 N07，不降低任何健康、地图或运动验收阈值。
- 决定：#308 离线几何证据不等于 SITL。#309 新冷启动在 N05 支架扫描第 7/15 阶段由 normalized cost 1.094002 > 1.0 拒绝，尚未到 post-release N05 或 N08 mission。
- 安全：fixture 已确认移除且 PX4 landed/disarmed；bridge DISABLED/control0；只停止本次容器，退出码 0。
- 下一步：因 #305 的同路线曾达到 post-release N05，而本轮是单一视觉 cost 尖峰，进行一次独立 cold-start 复现。若相同返程段再次健康锁存，则停止重复该路线并根据两次证据设计新 profile。N08 仍未完成。
- 证据：`progress/evidence/n08-prescan-localization-refusal-20261026-309.md`。
