# N08.2k #221：真实顶板与 baseline layout 同场景验证

## 假设、唯一变量与判据

- 相对 #218，唯一场景变量为在相同 `wall_box_column` 下增加真实静态 overhead panel；使用同一 −0.45 rad 支架观察和所有现有 N05/EGO 门限。
- 判据：N05 fresh post-release online/offline 通过；顶板表面 raw occupied；start／目标 body sphere、terminal-hold 邻域和完整候选曲线均应按既有 query 规则已知 free。任一 raw unknown 则不运行 compute-only，也不执行 XY。

## 结果

N05 profile 完成 15/15 stages。helper 报 `localization changed or became invalid during physical scan`，错误保留；scan 后和 fixture 释放后的 N05 gate 均以 `all_entry_phases_known_and_clear` 通过，online/offline 一致，same epoch/map。所有 PX4 记录为 DISARMED、最后 landed，支架 detached／不存在。运行结束后 `tools/project.sh stop` 返回 0。未发布控制／goal，未订阅真值。

新 layout 通过唯一 `wall_box_column` base config 复用 N04 的 box/column，scene manifest 同时记录 N04 与 N08 两份配置 SHA；新增模型为 8×8×0.1 m 顶板，底面 z=2.65 m。顶板 footprint 邻域（x/y ±4m、map z 2.1–2.7m）检测到 1,176 个 raw occupied voxels。

同一 fresh N05 post-release map、半径 0.730618 m：start body sphere 是 `0 unknown / 0 occupied`；`+Y 0.6 m` goal body sphere 也是全 free。加上现行 0.25 m terminal-hold neighborhood 后，start sphere 有 41 unknown，goal sphere 有 16 unknown。按生产 `certify_line` 等价计算，0.6 m 候选线的中间 body-sweep 查询通过，失败只发生在 `terminal_hold_neighborhood`，其中 16 unknown。因此没有启动 compute-only。

未知单元中心集中于 start 后方 y≈−1.05 m、z=[0.75,1.35] m，以及目标前方 y=[1.25,1.45] m、z=[0.95,1.35] m。可复算数据、map 哈希和完整坐标见 [JSON 报告](n08-overhead-ceiling-isolated-20261024-221.json) 与 run 归档。

## 判断与下一步

真实顶板让两个 0.730618 m body sphere 变为全 free，同时被 raw map 看成 occupied；它没有清掉额外 0.25 m terminal-hold 邻域的侧向未知区。#222 在同一顶板场景和 N05 门限下，只补充固定高度 yaw=−π/2 与 +π/2、pitch=0 的水平观察，再回中立。判据仍是 N05 online/offline、body/terminal spheres 和 full line 全 free；不满足就继续无 XY。
