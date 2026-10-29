# #313 对话摘要：低位 rear scan SITL

- 用户授权继续完成 N08；飞行任务仍是单程前向，到点停止，返航不隐含发起。
- #313 profile 静态 44 项测试通过；D435i 视场计算支持低位上仰观察，但不替代 raw-map 几何验收。
- SITL 中，先做低位回收没有复现 #307/#312 的下降锁存；yaw 和 pitch 同时移动时 normalized cost=1.022129 越过原门限，扫描完成 13/17 阶段。
- 无 post-release N05、mission 或飞行。fixture 已安全脱离，独立读回 DISARMED/landed/DISABLED、控制0，#313 容器退出0。
- 下一步 #314 保持路线和阈值，只拆分低位 pitch-up 和后向 yaw 转动；任何门失败都不发 goal/enable。
