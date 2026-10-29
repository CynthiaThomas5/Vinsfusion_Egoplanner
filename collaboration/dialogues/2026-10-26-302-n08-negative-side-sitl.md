# N08 #302 侧视路线 SITL 中止

- 已实现 profile：#300 的 overhead/free-sector 路线不变，插入负 Y yaw−π/2 / pitch0 侧视两段与 yaw回中。36项静态测试通过。
- SITL：15/18阶段，负 Y 侧视已实际到达并保持，随后 yaw0回中；刚开始下降回收时 normalized_cost=1.025847 超过原1.0门，锁存并未生成 post-release N05 map。初始N05拒绝保留。
- 安全：cleanup确认fixture已拆除/场景不存在/landed；独立读回 PX4 disarmed/landed、bridge DISABLED、控制0。Localization lockout保留，不使用旧状态继续任务；容器 exit0。
- 下一步：#303只在回中后增加15s中立保持，再回收；观察阈值完全不变。
