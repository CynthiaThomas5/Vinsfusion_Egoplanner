# #546 N14完成审计

N14限定可通行窄道出口通过：#541/#542/#543同发布运行版本，三个独立epoch/goal、真实GUI冷启动，正常任务3/3合格。通道净宽2.4m、长6m、墙高3m；运行候选相对N13仅世界文件变化，生产二进制、控制/定位源码、速度/加速度/yaw上限/膨胀保持，不恢复最小净空数值门。范围是当前仿真场景，不是任意宽度保证或实机资格。

| run | 通道内实际中心最大绝对y（m） | 左/右穿越前支持快照数 | 执行匹配轨迹数 | 违规接触 |
| --- | --- | --- | --- | --- |
| #541 | 0.020582 | 3 / 3 | 23 | 0 |
| #542 | 0.026931 | 1 / 1 | 23 | 0 |
| #543 | 0.027866 | 4 / 4 | 23 | 0 |

三次实际/参考路径完整从x=-3m入口穿过到x=3m出口，样本位于通道内，无外绕/飞越替代；双侧墙在进入前已有同身份同快照raw/inflated支持，匹配goal/epoch轨迹实际执行。独立到达、完整接触记录、正常落地上锁/控制归零、身份/参考点/输入哈希、GUI窗口及唯一控制发布者全部PASS，在线真值禁用。三次复用12m目标含0.1m高度变化及0.2rad不同yaw，核对实际运行goal profile，不另飞组合要求。

运行身份923ac373da0e695befea074ad605ae82e9ae2efba2707e1e8b1c0c247891c2ea，三次相同；epoch和goal互异；每容器镜像核对锁定099ab9af…；#540发布inventory核对当前配置和评估器字节身份。正式原始数据artifacts/runs/n14-20261029-{541,542,543}-formal{01,02,03}，完整报告在各自artifacts/reanalysis/<run>-evaluation/<run>/n14-scene-acceptance.json。原始报告不覆盖。

负目标另测#545：以实际VIO/map坐标查询分类后，分别向已观测占据点、raw未知但planning膨胀占据的遮挡点提交真实action，两次均STATUS_ABORTED/outcome rejected/reason map_query_occupied，未转发匹配EGO目标。未知本身仍按原生official_ego允许，本证据不声称所有未知点都会拒绝；拒绝依据是当前planning占据。raw球查询用0.01m、planning点查询0m，记录各自请求/回执半径、身份与分类，不混同语义，不新增known-free门。全过程未使能控制、未武装；12秒独立地面读回及安全停止全部checks通过。负例不计正常成功次数。

首个地面#544因raw球查询错误用0m得到invalid_query，未发目标即判不足并安全停止，原错误/报告保留；#545按源码要求修正接口后真实重测通过。此项不是飞行失败，也未通过改运行门限处理。

验证：106项新旧策略/几何/身份单测PASS；三次真实完整SITL及完整独立评估PASS；两类真实action拒绝和地面安全读回PASS；completion_audit.py逐项实际执行PASS，检查三份完整报告/源哈希/发布配置、runtime/独立epoch-goal、通道几何与双侧地图支持、GUI/控制发布者、真实终态及所有N14容器停止。结构python3 tools/project_status.py及git diff --check通过。无ROS/PX4运行代码变更，不以结构检查替代上述真实任务。

[机器完成审计和脚本](../../artifacts/runs/n14-20261029-546-completion)。报告路径/sha、运行身份等在completion-audit.json；负目标原始报告artifacts/runs/n14-20261029-545-negative-targets/negative-targets.json，地面终态ground-safe-stop.json，探针源码/驱动#545 negative-preparation与driver目录。全部N14会话已安全停止，无关容器保持。

未解范围：#521独立VIO/地图/资源数值仍为诊断，不称历史漂移等问题修复；不覆盖N15故障、N16十分钟、N17或实机。停止原因：用户指定N14全部出口已完成。下一主线N15，未执行。
