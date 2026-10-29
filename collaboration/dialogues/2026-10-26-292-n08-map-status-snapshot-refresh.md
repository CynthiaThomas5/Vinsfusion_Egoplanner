# N08 #292 MapStatus snapshot 顺序修复

## 用户约束

继续完成 N08 当前 Goal 出口；普通单目标到达后停止。返航若需要，用户会另发第二段命令，先停止 EGO、原地转 180°，再按 EGO 前向规则回原点。N07 已通过项不复测；不得降低速度、健康、地图、轨迹或 landing 门限。

## 决定与进展

#291 N05 支架扫描 6/6、夹具拆除、post-release online/offline 准入、40.004 s 只读 preflight 和当前区域 N05 均通过。runner 随后在起飞 snapshot 前因 MapStatus 门禁退出，`action_goal_sent=false`、无 enable 调用；独立读回为 bridge DISABLED、PX4 disarmed/landed、控制输出话题为零。旧 snapshot 流程在同步等待 service 前检查状态缓存，等待期间没有显式刷新状态回调；#292 改为等待 service 后 spin 获取新 MapStatus，再执行相同身份和就绪门禁，并添加专项回归。

仓库测试 348 项和 navigation-adapter integration 通过；ROS snapshot admission 专项 8 项通过。下一步新冷启动 #292 重做 N05 与所有 mission 前置准入，然后继续 motion-cancel 实测。N08 未通过，不进入 N09。
