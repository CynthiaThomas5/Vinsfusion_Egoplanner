# #536 N13完成审计

N13限定错位多障碍仿真出口通过：#531、#534、#535三个独立epoch/goal，在同一运行版本与同一修正版功能评估策略下全部PASS。#531保留原不足报告，通过明确原launch/protocol哈希的证据处理修复后完整重评；#534/#535直接按该发布执行。没有把N12或校准数据计入。#527/#530飞行前启动失败保留，不计正式飞行。3次实际正式飞行全部合格。

| run | 柱1/2/3穿越前支持快照数 | 已执行匹配轨迹数 | 支持的地图融合更新时间数 | 违规接触 |
| --- | --- | --- | --- | --- |
| #531 formal01 | 1 / 2 / 1 | 156 | 3 | 0 |
| #534 formal02 | 1 / 1 / 1 | 153 | 2 | 0 |
| #535 formal03 | 2 / 3 / 1 | 171 | 4 | 0 |

三次均有实际及参考路径绕过三柱、goal/epoch匹配样条、同身份同快照raw/inflated地图观测及更新、独立到达、完整接触传感器、正常落地上锁/控制归零和GUI窗口证据。新运行版本87eae3f768abe31e898e5402c77b17b54884fa029dc876c0a102792b5aba6d2e，仅世界文件相对N12候选变化；速度/加速度/yaw上限/膨胀及生产二进制保持。镜像逐容器核实为锁定099ab9af…；三个独立epoch/goal不同、runtime一致。控制发布者唯一，在线真值禁用。安全终态全部checks通过后已停止全部N13容器，未触碰无关容器。

完成审计实际检查所有必需指标及原始终态、GUI哈希、源文件/发布配置身份、报告哈希、逐柱几何/快照支持和实际轨迹执行。机器审计及脚本：[completion目录](../../artifacts/runs/n13-20261029-536-completion)。正式报告路径、sha、epoch、goal、runtime详见completion-audit.json；#531完整报告在artifacts/runs/n13-20261029-533-evaluator-release/formal01-complete-reassessment.json，#534/#535在各自artifacts/reanalysis/<run>-evaluation/<run>/n13-scene-acceptance.json。原始归档artifacts/runs/<run>，评估视图独立生成，原始报告未覆盖。

验证：97项新旧策略单测PASS（tests.txt在#533发布目录）；completion_audit.py实际执行PASS；python3 tools/project_status.py、git diff --check通过（日志在completion目录）。结构检查不代替上述三次真实SITL飞行。修复重复源戳/快照视图属于证据处理，未降低数值标准；旧失败/不足不覆盖。

未解范围：独立VIO/地图/资源数值仍按用户#521为诊断，不能据此声称漂移或地图分类问题修复；此结论不覆盖窄道、故障退出、连续十分钟或实机。N14–N17保持未完成。停止原因：用户指定N13全部出口已完成；唯一下一主线N14，未启动其任务。
