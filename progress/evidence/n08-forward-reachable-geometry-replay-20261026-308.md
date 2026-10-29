# N08 #308：X500/D435i 单向可达几何离线复算

状态：几何实现及静态验证通过；本报告只证明归档 raw map 的离线查询，不代表实时准入、起飞、飞行或 N08 通过。

## 结果

复用 #305 的同身份归档地图与起点。原球形门在单目标前向走廊首个查询遇到 217 个 unknown；motion-cancel 起点保持查询遇到 105 个 unknown。它们位于机尾后向视角缺口。

新查询使用锁定的 10 个 X500/D435i SDF 碰撞件。每个碰撞件使用保守 AABB 上界，并纳入现有 0.248682m 空间不确定度、实测最大 0.15m 跟踪误差、0.05m 侧／垂管道、7.5cm 前向查询偏置、5mm 初始回摆和不大于25mm的连续采样间隔。起点保持和终点保持独立检查；0.25m 总 tracking allowance、unknown／occupied／越界拒绝规则均保持。

固定航向角范围为 ±0.019rad。依据既有 N08 #294 运行的 2,106 对 PX4 local heading／PositionCommand 样本，最近 wall-time 配对的最大偏差为0.015545rad，最大配对间隔0.000822s；同一 0.019rad 范围用于样条 yaw 和实时 VINS yaw 保护。该观测来自旧运行版本，故只作为候选几何范围依据；#309 起的实时运行会重新记录并验证。它不替代任务配置的0.35rad目标 yaw 容差。

| 归档轨迹 | 扫掠查询 | 起点保持 | 终点保持 | 最大中心偏移／允许值 | 结果 |
| --- | ---: | --- | --- | ---: | --- |
| 普通单目标 +0.6m | 25 | free，unknown 0，occupied 0 | free，unknown 0，occupied 0 | 0.250778／0.262500m | 通过离线几何 |
| caller-cancel 0.5m停车走廊 | 21 | free，unknown 0，occupied 0 | free，unknown 0，occupied 0 | 0.250778／0.262500m | 通过离线几何 |

所有逐点查询均无 unknown／occupied。机器报告保存了同一地图和 SDF／配置／代码 SHA256、全部查询结果及 #294 航向测量复算。

## 实现与验证

- `certify_forward_trial_corridor` 已用于目标走廊和取消停车走廊；普通单目标仍在目标点停止，做独立目的地下降准入后落地，不隐含返航。
- runner 对固定航向的 B 样条 yaw 和实际 VINS yaw 使用同一 ±0.019rad 几何界；单独的180°转头分支不套用该直线航向界。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_n08_trial_gate`：28项通过。
- `bash tools/project.sh test`：374项全仓单测通过；navigation adapter integration 通过。
- `python3 -B` AST 解析三个运行／诊断脚本及定向测试通过；`git diff --check` 待最后交接前复核。

## 下一步

#309 使用新冷启动及已验证的 `n08_overhead_free_sector_negative_y_side_view` 剖面，重新执行支架扫描、释放后和 mission 当前区 N05、只读 preflight 及新 N08 几何门。只有同一 run、同一 epoch/map 的准入全部通过，才允许执行目标；若拒绝则记录最早失败门并安全确认 landed/disarmed。此离线证据不计为飞行次数。

详细机器结果：[JSON 报告](n08-forward-reachable-geometry-replay-20261026-308.json)。
