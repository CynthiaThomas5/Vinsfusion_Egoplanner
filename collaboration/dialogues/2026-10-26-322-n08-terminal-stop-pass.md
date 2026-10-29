# N08 #322 普通 single_goal terminal-stop

- 执行范围：N08 Goal 完成模式。用户确认普通目标到达即可结束；不发返航命令。N07 已通过项不复测。
- 冷启动、N05 支架扫描、fixture 移除、同身份 post-release 在线／离线准入、只读 preflight 和 mission current-area 准入均完成。N05 helper 最后短暂报 localization receipt stale，但后续独立 fresh 准入接受，原始告警保留。
- 普通 0.6 m 前向目标 action succeeded；独立位移 0.59726 m。参考／实际峰值速度 0.07915／0.07550 m/s，停车路径 0.28106 m，持续减速响应 1.504 s，最大独立误差 0.08008 m，停后 3 s hold 通过。
- full-body corridor 25/25 free，reachable bound 0.250778 m、available 0.262500 m；目标前后 landing candidate 通过。没有 return action/goal。
- evaluator 无绘图通过全部 checks；独立 PX4/bridge readback 为 LANDED、disarmed、控制关闭、控制样本0；容器停止退出0。外层 mission 仍受缺少 optional matplotlib 的 --plot 退出1影响，已与 native PASS 和独立 evaluator 区分记录。
- Runtime-contract SHA 与 #321 相同：75aaa541f7684b38fe0805b958e029fa21f8c6dd6ab00d2ebe1fae92c7e8a772。当前普通目标重复为1/3，N08保持in_progress。下一项#323沿用相同冻结来源和全部阈值。
