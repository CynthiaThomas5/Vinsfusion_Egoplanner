# N08 #324 普通 single_goal terminal-stop

- 运行范围：同冻结版本做第2个独立普通 terminal_stop；成功后到达即结束，不返航。N07不复测。
- N05支架扫描完成、fixture移除、同身份post-release在线/离线准入通过。fixture helper末尾有receipt-stale warning，fresh复查通过并保留原告警。
- 40.009秒preflight通过，optimized odom最大接收间隔0.11268秒、overguard0；current-area gate通过。25点full-body forward capsule、hold和终点landing candidates通过。
- 普通0.6m EGO goal action成功；实际位移0.59902m，参考/实际峰值速度0.07948/0.08282m/s，制动路径0.28868m，减速响应0.816s，独立最大跟踪误差0.08379m，3秒hold通过；不发返航goal。
- 无绘图独立evaluator全部通过；postmission独立读回LANDED、PX4 disarmed、control disabled、控制topic计数0；容器exit0。wrapper的optional matplotlib错误保留。
- Runtime contract SHA仍为75aaa541f7684b38fe0805b958e029fa21f8c6dd6ab00d2ebe1fae92c7e8a772。普通到达累计2/3，下一项#325。
