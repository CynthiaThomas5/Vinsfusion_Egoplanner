# 2026-10-26 #359 N10 高速取消制动

## 范围

继续 N10.3 的一次高速 caller-cancel 制动诊断，固定使用 PX4 水平速度 0.50–0.56 m/s 触发窗口。#358 是 ROS setup 脚本和 bash nounset 冲突，未进入 preflight，已独立读回 DISABLED/landed/disarmed/控制关闭/控制样本0并安全停止。

## 固定条件

继续使用 #357 的单 D435i 16 m 目标、0.8 m/s/轴、0.25 m/s²/轴、5 m horizon、起点和运行级定位质量/源龄旁路。保持 normalized-cost 原阈值和 official_ego inflated-occupied 碰撞策略；不运行额外 raw-free 全曲线拒绝门。唯一变量为已预先写定的取消触发速度窗口。

## 目标结果

记录 PX4 实测触发速度、EGO 参考速度、取消确认、替代轨迹、停止响应与独立真值制动距离，完成 contact/观察器和独立 PX4 末态读回。此单次样本只作诊断，不代表速度保证、健康资格或净空通过。
