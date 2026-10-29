# N10.3/#427.2 修复后的 depth-only 故障校准

结果：单次隔离深度断流端到端校准 PASS，父 N10 仍 in_progress。新运行 `n10-20261028-427-fault-repair-depth-calibration-r02`；runtime SHA `7d0559bba1f1f8f9d9da2d034b1e9cc246a4f19490ed997e9361c33541b0a3c3`。

- 故障窗口3.0仿真秒，丢91帧depth，之前/之后转发1080/526帧。窗口内左右图各91帧、IMU 750条，确认为depth-only。
- native EGO报depth_odom_timeout；匹配goal/epoch的action ABORTED。触发至bridge LANDING为0.664仿真秒，至LANDED/disarmed为6.096仿真秒。runner确认未在预期故障后发送operator disable。
- 独立15秒终态读回含12.197秒稳定终态：landed/disarmed/control-disabled、零终态后控制、无匹配旧身份活动轨迹、零终态离开。PX4 EV与本地位置仍有效，未复现#415的invalid-quaternion和无效XY/DESCEND。
- 只读sensor capture evaluator PASS；contact sensor就绪、禁止接触0、着陆地面接触有记录。
- 确认safe-to-stop全部检查后 `docker stop -t 30`，容器exit0。未使用紧急disarm，无活动项目飞行。

## 范围和缺口

本结果支持当前修复版本的depth-only故障链，不能证明#415根因或无效定位DESCEND路径已修复，也不计冻结后的N15正式次数。此处postflight probe开始太晚，ACK列表为空；故障期间ACK未由该observer保留，不能宣称完整ACK时序证据。下一次综合诊断应从目标提交前启用连续只读probe，覆盖ACK和模式变化；#426原始四元数故障日志已可记录异常。

首次同编号运行因传入相对sensor bridge路径被脚本拒绝，在bridge启动前exit12，无目标/解锁，原记录保留；r02使用要求的/workspace绝对路径。身份/prelaunch/tool-freeze全部为当前代码新生成。复用了#405的协议与飞行输入，未放宽门限。

## 验证与产物

`bash -n` runner通过；新runtime prelaunch与单快照native preflight通过；driver exit0；depth terminal、sensor capture和contact三个独立评估通过。hash及原始产物索引见同名JSON。结构检查与git diff --check另行执行。未改飞行源码；只修改本轮复制的runner/prelaunch并增加取证检查。

下一子项#428：固定#415同输入综合诊断方案，加入从飞行前开始的只读状态/ACK记录，验证#426故障证据捕获并追查四元数来源；随后继续缺失故障类别、数值标准和N10.5–N10.7。

对话摘要：../../collaboration/dialogues/2026-10-28-427-n10-fault-calibration-result.md
