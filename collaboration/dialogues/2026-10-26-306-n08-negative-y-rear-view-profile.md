# N08 #306 后向视角静态变体

## 依据
#305同身份raw map显示：cancel-stop start hold 105 unknown、首扫掠136、terminal hold14；0.6m capsule首query217。unknown中心主要位于x≈−1.05m后向薄层。负Y侧视完成但未解除该缺口。#233亦有后向start-hold未知体积，先前诊断建议做独立支架后向观察。

## 决定
#306沿#305的同一support scan路线，在回收前添加yaw−π后向观察，按−π/2分段转入和回中。只多24仿真秒，任务仍是向前单目标；该扫描只用于视角补图。所有阈值保持。

## 静态验证
40项profile测试、JSON、shell语法、项目结构和diff check通过。下一步全新SITL，post-release/current-area N05与N08 corridor/start/terminal hold全通过前不发目标或解锁。

证据：[静态报告](../../progress/evidence/n08-negative-y-rear-view-profile-20261026-306.md)。
