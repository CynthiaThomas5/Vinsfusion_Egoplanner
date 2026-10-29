# 2026-10-27 N10 #362：当前 gate-free runtime 停车量测重复

## 目标

继续 N10.3。对 #359 的 PX4 0.50–0.56m/s caller-cancel 停车测量做一次同配置、当前 gate-free runtime 的独立重复。所有速度/距离仍作诊断，两个样本不构成通用停车保证。

## 冻结条件

EGO 0.8m/s/轴、0.25m/s²/轴、horizon 5m；单 D435i、+16m/+0.1m/+0.2rad 目标、同一 spawn、official_ego、contact观察器、PX4 bridge。当前源码哈希须与 #361 相同。项目自加定位质量和定位/优化里程计回执龄门限保持已删除，原始指标仅观察；地图/EGO融合新鲜度和PX4桥控制规则保留。

协议与runtime snapshot见 `progress/evidence/n10-cancel-stop-gatefree-speed050-protocol-20261027-362.md`。

## 结果与后续

本次量测完整，11/11 检查通过：PX4 触发水平速度 0.500180m/s，真值水平停止路径 1.260994m，6.76 仿真秒进入停止带。零禁止接触；独立读回 landed/disarmed/control-disabled/zero-control，安全停止后容器已退出。与 #359 两个样本的路径相差约 0.04348m，但停车时间及减速度也有差异，不能据此宣称通用停车保证。#362所在世界含静态障碍，但本次报告没有单独计算障碍净空；动态障碍重规划和故障注入仍缺。详见 `progress/evidence/n10-cancel-stop-gatefree-speed050-20261027-362.md`。
