# N08 #294：运动取消停止链通过独立评估回放

## 结论

#294 的 native `flight.json` 为 PASS；任务前准入、caller-cancel、替换停止样条、实测保持、终点 landing 候选、landing command 和 landed/disarmed 均有证据。首次离线 evaluator 因同一 source stamp 上旧轨迹1与新认证轨迹2的handoff报“冲突”。评估器修复后，对原始不可变 run 输入做只读回放，35项检查全部通过。回放评估器 SHA 与 run 时记录的 evaluator SHA 不同；控制 runner、地图、飞控和样条数据均来自原 run，没有改变。

## 运行与制动测量

- N05 扫描6/6，post-release 与 mission current-area online/offline准入接受；40.002秒只读preflight通过。
- motion-cancel 在 PX4水平速度 `0.04021 m/s`、EGO参考速度 `0.05760 m/s`时触发。action status=5、outcome=`canceled`、reason=`caller_cancel`、success=false。
- 轨迹1切换至 live-certified轨迹2。两条命令在相同source stamp `354.520 s`相遇；位置差 `0.000492 m`、速度差 `0.000174 m/s`、加速度差 `0.0000264 m/s²`、yaw差 `0.001575 rad`。新轨迹的 live certificate明确从该source stamp开始，因此 evaluator选择新轨迹状态用于单调时序测量，同时将两状态差留在交接报告中。
- 停止样条向量速度界 `0.08961 m/s`（上限 `0.12 m/s`），reference tube／raw-map证书通过；native runner确认 READY末端零导数、PX4速度门保持3秒（151 unique local-position samples），期间bridge ACTIVE，旧轨迹未恢复。
- evaluator回放测得实际峰值向量速度 `0.08791 m/s`、停止距离（参考减速开始至实测停车）`0.20035 m`、取消请求至停下的行程 `0.30992 m`（4.712秒）、取消至持续减速响应 `2.852秒`、实际最大参考误差 `0.09020 m`、停后1秒位移最大 `0.01215 m`。取消停车距离小于本试验候选0.50m边界；本结果只支持该低速前向窗口，不推广为一般取消保证。
- destination pre-goal与final raw-map landing candidate均接受；PX4 bridge正常 landing command是在认证停止保持后发出。独立5秒读回确认bridge `LANDED/control disabled`、PX4 `DISARMED/landed`、控制消息0；容器随后停止并退出0。

## 评估器交接规则

只接受在新live spline证书source stamp上的同目标、同epoch、不同trajectory ID状态替换；位置／速度／加速度／yaw差全部记录。同轨迹的相同source stamp状态差异、无证书handoff和source-time倒退继续FAIL。完整回放结果与原始失败报告都保留在run目录。

原始输入及回放报告：`artifacts/runs/n08-cancel-translation-prescan-20261026-294/diagnostics/`。回放 evaluator SHA `131b3ba9…baa33f`，run时锁定 SHA `84d61efc…a17842`；该差异只来自本次离线评估规则修正，后续正式run会锁定当前 evaluator。
