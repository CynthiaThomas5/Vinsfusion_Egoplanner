# N08 #253：小俯仰扫描取得起点与前向保持净空

15/15阶段完成；same-identity after/post-release N05 online/offline准入通过。helper最后保留localization changed错误，但最终状态valid、支架detach/remove及新鲜landed已确认。归档raw map离线复算：起点及前方0.6m的0.980618m保持球unknown=0、occupied=0；按0.025m间隔加半采样cover的24次连续前向capsule查询也全部free。旧侧向hold unknown缺口在本轮观测范围内补齐。

沿路径任意位置的额外落地研究并未全部通过，x=+0.2m的TAKEOFF_CONTACT因raw occupied触及扩展机体而拒绝；保留原N05规则。本次计划内末端停车测量正常结束后返回原N05起降点，不声称任意接地点通过。

用户中断后仿真继续空闲约12小时，恢复时已锁存telemetry_stale。该epoch未发mission/goal，不能复用为新鲜飞行资格。独立读回DISARMED、landed、bridge disabled、零控制样本，Gazebo确认fixture不存在；project stop与容器均exit0。

下一#254以同版本／同扫描profile新冷启动取得实际曲线验证，随后才执行新鲜同run准入的受控制动试验。
