# N08 #290 build fingerprint 前置拒绝

## 任务与用户约束

继续用户授权的N08 Goal完成模式。普通单目标抵达即停止；返航为用户单独发出的第二段命令。N07不复测。保持N08速度、地图、健康、tracking和未知空间门不变。

## 结果

#290 fresh N05 VINS epoch `d213cae…`完成6/6，夹具移除确认、post-release N05 online/offline接受；40.001s只读preflight和mission current-area N05通过。motion-cancel runner在goal/enable前因仍使用#276/0046 build fingerprint而拒绝当前`dependencies/sources.json`（含0047）。未发布goal或控制。独立final probe为bridge DISABLED、PX4 disarmed/landed、三类控制topic 0，项目容器停止。

## 修复与下一步

为0047新增#289 build evidence并更新runner引用。17包ROS build、348项回归及导航adapter integration、ego source/patch replay通过。下一步#291使用全新冷启动，复做N05流程，并在通过所有preflight之后验证cancel stop spline、旧轨迹不恢复、实际停车/保持及末态。
